# Phase 3 — Structural checks in `validate_document`

**Depends on:** Phase 2 for the wiring (work items 6–10). The MCP-side checks (work items 1–5) need
only phase 1, so they can be built in parallel with phase 2. They use phase 1's
`SkeletonIndexParseError` (work item 2), and B9 uses phase 1's denylist.
**Blocks:** Phase 4. Its new sections need somewhere to be checked, and its finalizer needs checks to
repair against (README "Why this order"; cross-cutting risk 4).
**Risk:** medium. The checks are deterministic and unit-tested, so they are unlikely to be wrong in
the obvious ways. The real risk is **false positives**: a finding the architect cannot fix burns the
two-round repair budget and lands on the user as an "unresolved checks" decision. Every rule below is
deliberately narrow for that reason.

## Start here

**Prerequisites.**

- **Work items 1–5 (MCP side):** `uv run pytest -q` is green, and phase 1 is complete (README phase 1
  probe; `grep -n "class SkeletonIndexParseError" src/utils/skeleton_types.py` prints a match).
- **Work items 6–10 (wiring):** phase 2 is complete. Both lines of the README phase 2 probe (phase
  2's own "Already done?") must print nothing:

  ```bash
  grep -L "## Decisions needed" src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/templates/commands/phase_command.py
  grep -n -E 'post_synthesis|AUTO_API_PROMPTS|phase_mode == "shape"|Task\(bp\)|--no-verify' src/platform/templates/commands/phase_command.py src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/template_helpers.py src/platform/models/phase.py
  ```

- **B9:** phase 1's guard passes: `uv run pytest -q tests/unit/templates/test_phase_language_neutrality.py`.
- **B12 and work item 4:** phase 2 deletes `technical_phase_template` from `phase_command.py` and
  re-points both importers to the architect's constant (phase 2 work item 6):
  `tests/unit/templates/test_phase_section_references.py:21` and
  `tests/unit/models/test_content_loss_detection.py:21`. If the second still points at
  `phase_command`, phase 2 missed it: re-point it to
  `src.platform.templates.agents.phase_architect.technical_phase_template` before extending the
  file.

**Already done?** Both of these must print a match:

```bash
grep -nE "async def validate\(" src/mcp/tools/phase_tools.py                  # MCP half (work items 1-5)
grep -n "structural_findings" src/platform/templates/commands/phase_command.py  # wiring (work items 6-10)
```

Both were run on 2026-11-13 at commit `a64f0dc` and printed nothing, so this phase was not done.
On 2026-11-16, after stage S3 (work items 3–5), the first probe prints a match
(`src/mcp/tools/phase_tools.py:109`); the wiring probe prints nothing until work items 6–10 land.
After stage S4 (work items 6–9) both probes print a match, and so does the README probe: the
wiring probe finds the gate at the top of Step 9 (`src/platform/templates/commands/phase_command.py:872-874`).
Neither probe can match unrelated text:
- The `\(` excludes any future `validate_*` method. `phase_tools.py` has no `validate` method of any
  kind today; the only `async def validate` in `src/` is the base one (`src/mcp/tools/base.py:16`).
- A grep of `src/` and `tests/` on 2026-11-13 found no occurrence of `structural_findings`,
  `implementation_findings`, `paths_to_verify`, `skipped_checks` or `phase_structure`. `docs/` now
  contains them (this document), but neither probe reads `docs/`.

The README's phase 3 probe is the same pair as one line,
`grep -q "async def validate(" … && grep -n "structural_findings" …`. The `-q` keeps the first grep
silent, so the line prints output only when both halves have landed.

**Line numbers.** Every anchor was verified on 2026-11-13 at commit `a64f0dc`. Earlier phases edit some
of the cited files, so in these, re-find the anchor by symbol or marker text, never by line number:
- **Phase 2 rewrites** `phase_command.py`, `phase_architect.py` and `phase_critic.py`. Locate rules
  there by marker text, for example `Malformed Decision Entry`.
- **Phase 2 deletes and adds fields** in `src/platform/models/phase.py` and the phase builders in
  `src/platform/template_helpers.py` (its work item 3). Locate them by class or function name.
- **Phase 2 removes tests** from `tests/unit/templates/test_agent_templates.py`. Locate tests there by
  name.
- **Phase 1 adds** `SkeletonIndexParseError` to `src/utils/skeleton_types.py` and rewraps the error in
  `skeleton_generator.py` (phase 1, item 3). It also adds authoring notes to the materializers
  (phase 1, item 4).

The other anchors into `src/mcp/`, `src/models/` and `src/utils/` point at code that phases 1 and 2
do not edit.

**Re-verified 2026-11-16 (phase 3, stage S1, after phases 1 and 2).** The anchors that work items 1
and 2, the judgment calls and B2/B3 cite were re-found by symbol and corrected in place: the SD
writers in `phase_command.py`, `skeleton_types.py`, `skeleton_generator.py`, the materializers,
`loop_state.py` and the taught example in `phase_architect.py`. Other anchors are still as of
`a64f0dc`. Stage S2 then promoted `BULLET_PATH`, which moved the `skeleton_types.py` and
`skeleton_generator.py` anchors again; those were re-found and corrected in place too. Stage S3
found every work item 3–5 anchor in `src/mcp/tools/` and `src/models/` still at its `a64f0dc`
position, then moved them with its own edits; they are corrected in place, as are the moved
`template_helpers.py` and `create_phase.py` anchors in work item 5. Stage S4 re-found every work
item 6–9 anchor by symbol or marker after phase 2's rewrite, and corrected them in place; each
work item carries a "Landed in stage S4" block. The review fixes after S5 inserted lines into
`src/models/base.py` and `phase_command.py` Step 10.2; the anchors after those insertions (and the
`phase_command.py` writer anchors S4's gate had already moved) were re-found and corrected in place.

**Read first:**
- `CLAUDE.md`
- `docs/phase-refactor/testing.md`
- README "Shared contracts": "Subagent report format", "Relay protocol", "Critic findings" and
  "Section naming and frozen-reader compatibility"
- decisions.md, "Structural document checks live in MCP `validate_document`"
- findings F24, F25, F27, F28, F29, F31, F32, F33, F35 and F36
- the phase 2 document: work items 6–8 insert into the review loop it defines (its "new
  `/respec-phase` step map", Steps 9 and 10)
- phase 1, item 7: the `(verify: ask user — …)` marker that work item 2 must accept

**Recommended first action.**
1. Create `src/utils/phase_structure.py` with the four function signatures from work item 2, each
   returning empty results. Create `src/models/document_validation.py` and add
   `DocumentValidationResponse` to `src/utils/loop_state.py`, both from work item 1.
2. Write B1–B8, B17 and B18 in `tests/unit/utils/test_phase_structure.py` against small fixture
   documents, one defect per test.
3. Run them. They must fail on assertions, not on imports; that is why the stubs come first
   (testing.md, "The cycle").

**Judgment calls no test will catch.**

1. **When unsure, don't flag.** A false negative costs one defect the critic or a person may still
   catch. A false positive the architect cannot repair costs two wasted subagent rounds plus a user
   prompt. So:
   - Directory entries in Module Layout cover the files under them.
   - `OD-3` and `OD-003` are the same ID.
   - A `title:` prefix on an OD title is tolerated.
   - `- None` is a valid empty marker.
   - Unnumbered `SD-###` entries are accepted, because frozen respec-code writes them
     (`src/utils/design_conformance.py:287`, `:318`) and every orchestrator writer did before
     phase 2 (`phase_command.py:752` at `a64f0dc`). Phase 2's writers number their entries
     `SD-NNN` (`phase_command.py:1200` for `user-edit`).
   - SD sources already written to existing documents are accepted: `materializer`, `user-edit`
     with its extra `section=` key (`phase_command.py:1200`), and the legacy `user-menu` and
     `user-override`. Phase 2 converted the `user-menu` writers in the materialization block
     (`phase_command.py:1393-1428`, formerly `:906-947`) to `user` and `materializer`, so only
     documents written before phase 2 still carry `user-menu`.
   - An SD value may itself contain ` | `. Frozen respec-code writes a signature into `supersedes=`
     (`src/utils/design_conformance.py:316-319`), and an accepted unresolved check records each
     finding verbatim. A segment that does not start with a not-yet-seen known key continues the
     previous value.
   - Phase 1's `(verify: ask user — …)` marker is a valid verify command. It is the sanctioned
     fallback when no test command is configured (phase 1, item 7). The briefing owns that question
     (phase 2), and the architect could not repair the marker without guessing a command.
   - References inside SD entries and Research Requirements lines are not checked. SDs are settled
     history, the ledger is orchestrator-owned, and the architect carries both forward verbatim
     (phase 2, work item 5, `draft`), so no repair round could fix them.
2. **Never parse a target language.** Signature text is checked only against the meta-notation, with
   `parse_bare_signature`. Never consult a materializer, `language_for_path` or a file extension. The
   one parser the CLI shares with this phase is the meta-notation itself (F24).
3. **The meta-notation has a known gap.** On 2026-11-13, `parse_bare_signature` rejected
   `Accounts.valid?(user) -> boolean` and `Accounts.register!(attrs) -> {:ok, User}`: identifiers that
   end in `?` or `!` fail `src/utils/skeleton_types.py:6-9`. The CLI rejects the same lines: today
   with a traceback (F24), and after phase 1 with a readable `SkeletonIndexParseError`.
   - This phase **mirrors** the CLI. B2 pins parity, so the check follows automatically once the
     grammar is fixed.
   - Widening the grammar belongs to phase 1 / the grammar owner. Do not widen it here.
   - Until then, the architect cannot repair such a finding without renaming a real function, so it
     ends in the "unresolved checks" decision. That is correct: the CLI would reject the line at
     sign-off.
4. **The server is filesystem-blind on purpose.** The MCP server is one shared daemon on port 9876,
   started with no project volume (F29; `src/cli/docker/manager.py:196-206`). Even running locally,
   it has no notion of *which* project is calling. Do not add "check the path if it happens to exist
   on the server": that would make the same document validate differently per deployment.
5. **Structural repair after a user's hand edit must not undo the edit.**
   - The architect fixes structure around the user's change; `source=user-edit` SDs bind it.
   - It never rewrites a `source=user` entry's words.
   - It leaves unfixed any finding it could fix only by contradicting the user, and names that
     finding and the reason in one line of `## For the user`. It does **not** raise an `OD-NNN` for
     it: once the repair budget is spent, the gate already carries the finding to the user in the
     single "unresolved checks" decision. Raising an OD too would ask the same question twice.
6. **Finding text is a repair instruction.** The architect reads `detail` to fix the document, so
   each one:
   - names the exact subject, through the `subject` field. Every rendered form,
     `<check> <subject> [<part>] — <detail>`, carries it. `detail` refers to the subject as "this
     path", "this entry" or "this item" and never interpolates document text, because real paths
     carry extensions. IDs, `Step <N>` and known `source` values may appear in `detail`.
   - names the single correct fix
   - names no language, framework or file extension
7. **Check IDs are a contract.** Prompt text cites them, and the tests assert on `check`, `subject`,
   `part` and `owner`, never on `detail` wording. Renaming a check means updating the prompts in the
   same commit.
8. **Every finding has one owner, and only the architect's go to the architect.** Lines the
   orchestrator writes cannot be repaired by an architect round, because the architect preserves
   them verbatim. These are non-architect SD entries and the Research Requirements ledger. A finding
   on one of them carries `owner: orchestrator`. The gate puts it straight into the unresolved-checks
   decision instead of spending repair rounds on it (work item 7). Such a finding means an
   orchestrator template defect; log it in `deferred-issues.md` if a real run produces one.
9. **An accepted finding stays accepted.** The checks are pure functions with no memory. Without
   suppression, a finding the user accepted would be recomputed on the next Step 9 entry, burn two
   more repair rounds and be asked again. The server therefore drops any finding the user has
   accepted through an unresolved-checks SD (work item 2, "Accepted findings").

## Goal

`validate_document` becomes the deterministic owner of every mechanical check on a phase document.
Today those checks are prompt text the critic re-runs, non-deterministically, on every round.

**What it checks.** Pure, unit-tested functions check document structure only:
- seam paths against Module Layout
- the Skeleton Index meta-notation
- Test List entries
- decision and settled-decision entries
- ID integrity
- the `implementation.md` fields that exist today, when the body is passed

It also extracts the cited paths that only the host can verify.

**How it reports.**
- Structural findings are reported **apart from content loss** (F29). `status` and `message` keep
  meaning "content loss", so the hand-edit menu never shows a structural problem to the user.
- Content-loss detection extends to additional sections (F27), and agent writes now report their own
  content loss.

**How it is wired.** After every architect draft or revise, the orchestrator validates the stored
document. Mechanical problems go back to the architect, within the existing two-round repair budget,
before the critic runs and before the user sees anything. The critic stops carrying the rules that
moved.

## How the checks fit the flow

| Caller | Call | Uses from the result |
|---|---|---|
| Orchestrator, hand-edit path | `validate_document(doc_type="phase", content=<raw edited file>)` | `status` and `message` only: content loss, shown to the user because the edit is theirs (README "Relay protocol" step 5) |
| Orchestrator, review gate | `validate_document(doc_type="phase", key="<plan>/<phase>")` at the top of phase 2's Step 9, before the critic. Every path into Step 9 passes it, among them Step 8's draft, Step 9's own repair `revise`, every Step 10 send-back (change, hand edit, design-changing answer, relayed question, research follow-up), Step 11's design-changing answers, and Step 4's resume and re-open routes. | `structural_findings` only. Open architect-owned findings trigger an architect `revise` repair round; orchestrator-owned ones go straight to the unresolved-checks decision. |
| Architect, `draft` and `revise` | the same key-mode call, plus `implementation_markdown` (it writes `implementation.md` in both modes, phase 2 work item 5), after its last `update_document` | fixes every architect-owned finding and verifies `paths_to_verify` with its own Glob, before returning |
| Critic, `review` | key mode plus `implementation_markdown=<Read of implementation.md>` | `paths_to_verify`, checked with Glob, and `implementation_findings`, relayed as `[mechanical]` blockers. It never re-raises `structural_findings`, which the gate owns. |

**Why findings are recomputed, not transmitted.**
- Every check is a pure function of the document, plus the filesystem for cited paths. Any party that
  needs the findings can recompute them.
- So a repair round needs no new channel: the orchestrator invokes `revise` with mode and IDs only,
  per the Agents contract, and the architect finds the problems itself. This works only because
  `revise` always runs its structural self-check, even when `get_feedback` holds nothing new. It
  must never return early on "no new feedback" (work item 8).
- Routing them through `store_user_feedback` would be the alternative, but that channel is untagged
  and unbounded (F31). It would also file mechanical findings as user input.

**Why the critic verifies cited paths, not the orchestrator.**
- `implementation.md` has no MCP home (F29). Some host agent must pass its body to
  `validate_document`.
- If the orchestrator did it, the body would be re-emitted inside the user's conversation, which
  breaks the relay split.
- The critic already Globs these paths today (`phase_critic.py:590-633`, `:771-795`, pre-phase-2).
  This phase moves only the extraction into Python.
- The orchestrator writes `- Read:` lines only after confirming the file exists (README "Research
  recording"), so host verification is a backstop.
- **If phase 2 overturned the `implementation.md` open call** (decisions.md, "The writing agents put
  the `implementation.md` draft on disk themselves"), the orchestrator already holds the body. It
  then passes `implementation_markdown` in its own gate call, and the critic's relay of implementation
  findings is dropped.

**Evidence gathered for this phase** (probes run 2026-11-13; they extend F27):
- `Phase.find_content_loss` returned `[]` for each of these:
  - an unmapped `## Guardrails` holding `Rule one / --- / Rule two`, which stored only `Rule one`
  - a fenced ```` ``` ```` block containing a `## …` line inside `### Collaboration And Wiring`, which
    truncated the section at the fence
  - the same fenced line inside an unmapped H2
  - a fenced `### Test List` line inside `### Collaboration And Wiring`. It truncated that section
    at the fence and put the fence's tail into `test_list`. The fenced heading uses a mapped name,
    so orphan detection does not see it.
  - `## Design` placed after `## System Design`, where `## Design` captured `### Architecture`
- No loss occurs, and none must be reported, for a fenced `### …` line inside an **unmapped** H2:
  the H2-only extractor stops only at a `##` heading line and `---` (`src/models/base.py:94-103`),
  so the section round-trips whole. A fenced `### …` line with an unmapped name under a mapped H2
  is already reported as an orphan by the base implementation.
- `fastmcp` (3.3.1) serializes an `MCPResponse` subclass's extra fields through the tool layer, and
  publishes the return annotation as the tool's `output_schema`.
- For every Skeleton Index line tried, `strip_tags` + `parse_bare_signature` accepted and rejected
  exactly what `parse_skeleton_index` did. Both materializers call `parse_bare_signature` first, and
  nothing after it raises (`src/utils/materializers/python_materializer.py:34-44`, called from
  `parse_signature` at `:81-82`; `typescript_materializer.py:66-72`).

## Behaviors to pin (red step — write these first)

| # | Behavior the test protects | Lives in |
|---|---|---|
| B1 | A seam whose path is not in Module Layout is reported, naming the path. A seam under a Module Layout entry ending in `/` is covered. A phase with no Skeleton Index reports nothing. | `tests/unit/utils/test_phase_structure.py` |
| B2 | **Parity with the CLI parser:** the check flags a Skeleton Index signature exactly when `parse_skeleton_index` would raise (`SkeletonIndexParseError` after phase 1, a `ValueError` today). Parametrize the lines over a meta-notation line, a native-syntax line, and the two `?`/`!` lines above. Parametrize the path over one with no extension and one per registered materializer, taken from `_MATERIALIZER_MAP` and `EXTENSION_TO_LANGUAGE` rather than written as literals. The seam is also parametrized inside a backtick and a tilde fence, because the CLI does not skip fences (review fix). Validation itself never raises (F24). A column-0 backticked-path bullet with no ` :: ` signature, and an unquoted bullet containing ` :: ` at any indentation, are reported, because the CLI silently skips both (`src/utils/skeleton_generator.py:80-86`). | same |
| B3 | A column-0 Test List bullet whose first backticked span is not `<path>::<behavior>`, or whose behavior is empty, is reported. The CLI silently skips such entries (`skeleton_generator.py:113-114`). Trailing text after the span is allowed. Seams with an empty Test List are reported once; a fenced entry the CLI reads makes the list non-empty (review fix). | same |
| B4 | An OD entry with any of these problems is reported. There is one finding per defect, and `part` names it: missing title, Option A, Option B or Recommended; a Recommended that names an absent option; a fourth option; the retired single-line form. A canonical entry passes, with or without Option C, with or without a `title:` prefix, and with extra indented sub-lines. This carries the intent of `test_agent_templates.py:618` (a missing Recommended silently records an empty decision). | same |
| B5 | An SD entry missing a field its `source` requires (`part` names the field), or with an unknown or missing `source`, is reported. These pass: frozen respec-code's `- SD-### \| source=implementation \| supersedes=<member>(<params>) -> <result> \| reason=…`, with a ` \| ` inside the `supersedes` value; today's `source=materializer`, `source=user-menu` and `source=user-edit \| section=…` lines (`phase_command.py:752`, `:906-947`); and a `source=user \| supersedes=unresolved-checks` entry whose `decision` quotes findings that contain ` \| `, including a quoted SD line with its own `source=` and `supersedes=`. That last entry still reads as `source=user`, `supersedes=unresolved-checks`, because the first occurrence of a key wins. | same |
| B6 | A reference to an undefined OD, SD, CQ, FLOW or RP ID is reported. Settled ODs and CQs resolve through an SD's `supersedes=`. `OD-3` and `OD-003` are one ID. Fenced blocks are ignored, and so are references inside SD entries and Research Requirements ledger lines. Duplicate definitions are reported, and so is an OD that is still open after an SD settled it. A `- Read:` or `- Applied:` line naming an RP, and a FLOW-led bullet outside the flow list, never count as a second definition (review fix). | same |
| B7 | `- Read:`, `- Constraint:` (§ qualifier stripped) and `.best-practices/…md` paths are returned in `paths_to_verify` with their `kind` and where each is cited. A `.best-practices/` path on a `- Read:` line is returned once, as `read`. Paths in Settled Design Decisions are not returned (review fix). File existence is listed in `skipped_checks`. The result is identical whether or not the cited files exist where the check runs (`tmp_path` + `monkeypatch.chdir`, no mocking). | same |
| B8 | When an `implementation.md` body is passed, each of these is reported: no steps; a step heading that is not `#### Step <integer>: <title>` (frozen readers skip it, F33); a duplicate step number; a missing `## Build Order > ### Steps`, `## Checklist` or `## Policy`; a checklist item with no `(Step N)`, naming an unknown step, or with a verify command that is empty, `TODO`, `no_preference` (F25) or wholly a placeholder; a step no checklist item verifies. Phase 1's `(verify: ask user — …)` marker passes, and so does an item with one `(verify: …)` group per language. **The taught form passes:** the shipped `implementation_plan_example` (`phase_architect.py`), with each `(verify: …)` placeholder replaced by a concrete command, yields no findings. When no body is passed, the result says the check was **skipped**, never clean. | same |
| B9 | Findings never depend on a path's extension (parametrize over none and two synthetic extensions). Every finding's `detail`, from a corpus that triggers every check ID, and the published tool description pass phase 1's denylist. Import that list from where phase 1 put it. Phase 1 kept its scanner inside `tests/unit/templates/test_phase_language_neutrality.py`; stage S1 moved the list and the scanner to `tests/support/language_denylist.py`, and both guards import them from there; production never imports it. A negative self-test proves the denylist fires. The description half is `test_the_published_validate_document_description_names_no_language` (stage S1); stage S3 rewrote the description and re-ran it. | same |
| B10 | Structural findings never change `status` or `message`. A document with structural findings and no content loss returns `completed` with the unchanged "No content loss detected." message, so the hand-edit menu cannot show a structural problem. Content loss still returns `user_input`. A phase with no design layer (create-phase output) reports no structural findings. | `tests/unit/mcp/test_document_validation.py` (exists; extend it, keeping its two tests green) |
| B11 | Content that `store` would reject (bad title, F29) neither raises nor validates clean. It is reported to its author as content loss (the whole edit cannot be stored), and the structural checks are listed as skipped with the reason. | same |
| B12 | Content loss in unmapped H2 sections is reported: bare-`---` truncation, and capture by an earlier H2 whose name contains its own. A `##` heading line inside a fenced block is reported wherever it sits. A `###` heading line inside a fenced block is reported only under a mapped H2, including one with a mapped name such as `### Test List`. A fenced `###` heading line under an unmapped H2 is **not** reported, because nothing is lost there. An unmapped H2 whose name overlaps another H2 name is a **structural** finding, whatever the order (Postgres reorders additional sections, F27 trap 4). Plan and Roadmap content-loss results are unchanged. | `tests/unit/models/test_content_loss_detection.py`; the overlap half in `tests/unit/utils/test_phase_structure.py` |
| B13 | An `update_document` whose content loses text still stores, and its response names each heading that lost content. Frozen respec-patch also writes phases through it, so it warns rather than rejects. | `tests/unit/mcp/test_document_validation.py` |
| B14 | Key mode validates the **stored** document. Exactly one of `content` and `key` is required. `key` and `implementation_markdown` on a non-phase type are errors. The published tool schema lists `doc_type` as its only required input, and exposes `key`, `implementation_markdown` and the four result fields (`await mcp.list_tools()`, the probe above). Rendered calls therefore never name a parameter the tool lacks. | same |
| B15 | **The gate**, on all three TUIs (stage S4: `test_phase_structural_gate.py`; `template_contract` gained only a frontmatter `tools:` fallback in `declared_tools()` and `block_at()`). A key-mode validation runs at the top of Step 9, before the critic, so it follows every architect `draft`/`revise` and every stored hand edit. With architect-owned findings open and budget left, the orchestrator re-engages the architect in `revise`, and no user prompt is reachable on that path. Structural repair rounds draw on the same two-round budget as critic `[mechanical]` findings. Orchestrator-owned findings, and leftovers once the budget is spent, join the unresolved-checks decision. They survive a critic `completed`. The critic is not invoked on a failing draft while budget remains. When a content-loss line reads `The document cannot be stored`, the hand-edit menu offers no option that proceeds with the unstorable text. | `tests/unit/templates/test_phase_structural_gate.py` |
| B16 | **One owner per rule:** the critic raises none of the moved blockers (work item 9). It verifies existence only for paths in `paths_to_verify`, and relays every `implementation_findings` entry as a `[mechanical]` blocker. The architect and critic invoke only MCP tools they declare (Claude Code rendering, F14). The critic's grants gain only `validate_document`: no `Write`, `Edit`, `update_document` or `store_document`. | same |
| B17 | **An accepted finding stays accepted.** A structural or implementation finding is not reported when a `source=user \| supersedes=unresolved-checks` SD contains its finding key (work item 2, "Accepted findings"). It is listed in `skipped_checks` instead. These are still reported: the same finding with no such SD, or with only a non-`user` SD quoting it; and a finding on the same `check` and `subject` with a different `part`. Suppression still works when the accept SD quotes a finding whose subject is itself an SD line containing `source=` and `supersedes=`. | `tests/unit/utils/test_phase_structure.py` |
| B18 | **Ownership is computed, not guessed.** These findings carry `owner: orchestrator`: findings on an SD entry whose `source` is `user`, `user-edit`, `user-menu`, `user-override`, `materializer` or `implementation`, and findings on a Research Requirements line. Every other finding carries `owner: architect`, including findings on an SD with `source=architect` or with an unknown or missing source. | same |

- **B2, B6, B10 and B17 matter most.**
  - B2 is what makes "a Skeleton Index line that does not parse is a finding, not a crash" true
    (decisions.md, phase-3 constraints).
  - B6's `supersedes=` rule is the false positive most likely to loop forever: settled ODs are removed
    from Open by contract, and CQ IDs never enter the document.
  - B10 is the F29 separation. Without it, the hand-edit menu shows mechanical problems to the user.
  - B17 is what stops an accepted finding being asked again on every later round (judgment call 9).
- **B15 is a template-contract test.** Phase 2 defines the loop's step names, so write the assertion
  against structure: which invocation follows which call, and which branch contains `WAIT for`. Do not
  match prose. Grow `tests/support/template_contract.py` with the minimum it needs
  (testing.md, "Start the helper minimal").
- **Agent-level tests** must build `CodexAdapter` and `OpenCodeAdapter` with `model_overrides` (F37).

## Scope

### Part A — the MCP checks (no phase-2 dependency)

#### 1. Result models

New `src/models/document_validation.py`. It uses Pydantic v2 `BaseModel`, as `src/models/feedback.py`
does; the `BestPracticeModel` that `CLAUDE.md` names does not exist in `src/`. Enums follow
`src/models/enums.py`'s `(str, Enum)` style:

```python
class StructuralCheck(str, Enum): ...      # the check IDs in work item 2; prompts cite these values

class FindingOwner(str, Enum):
    ARCHITECT = 'architect'
    ORCHESTRATOR = 'orchestrator'

class CitedPathKind(str, Enum):
    READ = 'read'                      # a `- Read:` line in Research Requirements
    CONSTRAINT = 'constraint'          # a `- Constraint:` line in Implementation Plan References
    BEST_PRACTICES = 'best-practices'  # any other `.best-practices/…md` mention

class StructuralFinding(BaseModel):
    check: StructuralCheck
    location: str    # heading path, e.g. "Design Shape > Skeleton Index" or "implementation.md > Checklist"
    subject: str     # the offending path, ID or line, verbatim, on one line
    part: str = ''   # the element at fault when a subject has several, e.g. "Option B", "rejected", "verify"
    owner: FindingOwner
    detail: str      # one line: what is wrong and its single correct fix

class CitedPath(BaseModel):
    path: str
    kind: CitedPathKind
    cited_in: str    # heading path
```

Add the response model to `src/utils/loop_state.py`, beside `MCPRoadMapResponse`:

```python
class DocumentValidationResponse(MCPResponse):
    structural_findings: list[StructuralFinding] = Field(default_factory=list)
    implementation_findings: list[StructuralFinding] = Field(default_factory=list)
    paths_to_verify: list[CitedPath] = Field(default_factory=list)
    skipped_checks: list[str] = Field(default_factory=list)
```

- **Subclassing `MCPResponse`** (`src/utils/loop_state.py:22-28`) follows the `MCPRoadMapResponse`
  precedent (`:16-19`). It keeps `status` and `message` where `phase_command.py:702-748`
  (pre-phase-2) reads them.
- **Why `loop_state.py` and not `src/models/`.** No module in `src/models/` imports from `src/utils/`.
  `loop_state.py` already imports downward from `src/models/` (`src/utils/loop_state.py:6-9`), so it
  can import `StructuralFinding` and `CitedPath` the same way.
- **`CONTENT_LOSS_WARNING`** is a constant in `src/models/document_validation.py`, defined like
  `FROZEN_DISCARD_WARNING` (`src/utils/state_manager/base.py:29`). Prompts import it the way
  `create_phase.py:6` imports that one, so they can match it exactly (work items 5 and 8).

#### 2. The pure checks

New `src/utils/phase_structure.py`. It has no I/O, imports nothing from `src/utils/materializers/` or
`language_extensions`, and exposes four functions:

```python
def check_phase_structure(phase: Phase) -> list[StructuralFinding]: ...
def extract_cited_paths(phase: Phase) -> list[CitedPath]: ...
def check_implementation_structure(markdown: str, phase: Phase) -> list[StructuralFinding]: ...
def drop_accepted_findings(
    findings: list[StructuralFinding], phase: Phase
) -> tuple[list[StructuralFinding], list[str]]: ...
```

- **Input is a parsed `Phase`.** Checks read `Phase` fields, not raw text, so they see what
  downstream readers see (F32). Section-scoped rules read the typed fields. ID scanning reads
  the content `phase.build_markdown()` emits, one section at a time: each typed field and each
  `additional_sections` value is scanned on its own, so fence state never carries from one section
  into the next. Unmapped H2 names are the keys of `phase.additional_sections`.
- **Reuse only parsers that do not hide the defect being checked:**
  - **Reuse:** `strip_tags` and `parse_bare_signature` (`src/utils/skeleton_types.py:57-90`). Catch
    the parse error phase 1 introduces (`SkeletonIndexParseError`, a `ValueError` subclass); never
    catch a bare `ValueError`.
  - **Promote:** move the bullet grammar `_BULLET_PATH` from `skeleton_generator.py` into
    `skeleton_types.py` as a public name, and re-point `skeleton_generator.py`. `skeleton_types` is
    the bottom of the skeleton layering (`src/utils/skeleton_types.py:78-80`), and importing a
    private name across modules invites drift. Done in stage S2: it is now `BULLET_PATH`
    (`src/utils/skeleton_types.py:15`), and `parse_skeleton_index` and `parse_test_list` import it.
  - **Do not reuse:**
    - `parse_skeleton_index` or `parse_test_list` (`skeleton_generator.py:76-117`). They silently
      skip exactly the malformed entries this phase must report, and the first dispatches on file
      extension to materializers.
    - `review_weighting._BULLET_PATH`, which documents why it is deliberately lenient
      (`src/utils/review_weighting.py:31-36`).
    - `tests/support/plan_extraction.py`. Production never imports test code (`CLAUDE.md`). Its
      step-heading regex (`tests/support/plan_extraction.py:13`) is the grammar to match.
  - **There is no OD or SD parser to reuse** (F35). This module becomes the first.

**Phase checks** (`check_phase_structure`). Each check fires only when its section has content. An
unshaped phase reports nothing.

| `check` | Location | Fires when |
|---|---|---|
| `seam-path-not-in-module-layout` | Design Shape > Skeleton Index | A Skeleton Index path is not listed in Module Layout and does not start with a Module Layout entry ending in `/`. Module Layout paths are the backticked path of every bullet at any indentation, read with the promoted bullet grammar. Compare after stripping a leading `./`. |
| `seam-entry-malformed` | Design Shape > Skeleton Index | A column-0 bullet, other than `- None`, is not `` - `<path>` :: <signature> ``; or a bullet at any indentation has no backticked path but contains ` :: `. Indented bullets with a backticked path and no ` :: ` are notes and pass. |
| `seam-signature-unparseable` | Design Shape > Skeleton Index | A `` `<path>` :: <signature> `` line at **any** indentation (the CLI strips lines), fenced or not (the CLI does not skip fences), whose signature, with trailing tags removed by `strip_tags`, fails `parse_bare_signature`. Never raise. |
| `test-list-empty` | Design Shape > Test List | The Skeleton Index has at least one valid entry and the Test List has no bullet other than `- None`. Reported once. Malformed Test List bullets get only their own finding. |
| `test-entry-without-behavior` | Design Shape > Test List | A column-0 bullet, other than `- None`, whose first backticked span is not `<path>::<behavior>` with a non-empty path and behavior. Text after the span is allowed. |
| `decision-entry-malformed` | Design Decisions > Open Design Decisions | See "OD entries" below. One finding per defect. `subject` is the entry's ID as written (`OD-003`), or the whole line for a bullet with no ID; `part` is the defect. |
| `settled-entry-malformed` | Design Decisions > Settled Design Decisions | See "SD entries" below. `subject` is the entry's ID as written (`SD-007`), or the whole line for an unnumbered `SD-###`. |
| `section-name-overlap` | the H2 | An unmapped H2 whose name contains, or is contained in, another H2 name: a mapped one from `Phase.HEADER_FIELD_MAPPING` (`src/models/phase.py:23-52`), `Metadata`, or another unmapped H2. This enforces README "Section naming" at runtime. |
| `duplicate-id` | where the second definition sits | The same OD, SD, RP or FLOW number is defined twice. Unnumbered `SD-###` entries are exempt. |
| `settled-decision-still-open` | Design Decisions > Open Design Decisions | An OD is still listed open although an SD's `supersedes=` names it. README "Settled decision entry → Placement" says to remove it. |
| `dangling-reference` | the heading containing the reference | See "ID integrity" below. |

**OD entries** follow the canonical form in README "Subagent report format".
- **Entry line:** a column-0 `- OD-<digits> | <title>` line, with an optional `title:` prefix.
- **Sub-lines:** the indented lines up to the next column-0 bullet or heading. Sub-lines other than
  the ones below (for example `- Affects:`) are allowed.
- **Defects**, each one finding, with `part` in brackets:
  - an empty title (`title`)
  - no `- Option A: <text>` or no `- Option B: <text>` with non-empty text (`Option A`, `Option B`)
  - a letter beyond `C` (`Option <letter>`), or a repeated letter (`Option <letter>`)
  - no `- Recommended:` line (`Recommended`)
  - a Recommended whose first token, optionally prefixed `Option` and with trailing punctuation
    stripped, is not a present option's letter (`Recommended`)
  - the retired single-line form: `| Option A:` or `Recommended:` on the entry line itself
    (`single-line form`)
  - a column-0 bullet that is not an entry and is not `- None` (`entry line`)
- `Affects:` is optional, but its IDs are references (ID integrity).

**SD entries** are a column-0 `- SD-<digits | ###> | <segments>` line, with segments split on
` | `. Segment parsing:
- **A key segment** starts with a known key followed by `=`, and that key has not appeared earlier
  in the line. The known keys are `source`, `supersedes`, `decision`, `rationale`, `rejected`,
  `binding`, `section` and `reason`.
- **The first occurrence of a key wins.** A later segment that repeats a known key is continuation
  text, like any other segment.
- **Any other segment** is appended, with its ` | `, to the previous segment's value. This keeps
  frozen respec-code's signatures intact. It also stops a quoted finding from overwriting the
  quoting SD's own keys: an accept SD's `decision` can quote an SD line that itself contains
  `source=` and `supersedes=`.
- **Keys beyond the required ones are allowed**, for example `user-edit`'s `section=`.

| `source` | Required, non-empty (`part` names a missing one) |
|---|---|
| `user` | `decision`, `rationale`, `binding`; plus `rejected` when `supersedes` names an OD or CQ |
| `user-menu`, `user-override` (legacy: phase 2 retires both, and today's writers in `phase_command.py` become `user` or `materializer`; documents written before phase 2 still carry them) | `decision`, `rationale`, `binding` |
| `user-edit` | `decision`, `binding` |
| `materializer` | `decision`, `rationale`, `binding` (`phase_command.py:1407`, `:1414`, `:1423`, `:1428`) |
| `architect` | `decision`, `rationale`, `binding` |
| `implementation` | `supersedes`, `reason`: the frozen write-back form (`src/utils/design_conformance.py:285-287`, `:316-319`) |
| anything else, or missing (`part`: `source`) | defect |

The required fields beyond the README's single `source=user` example are new contract text. Work
item 10 adds this table to README "Settled decision entry". `supersedes=unresolved-checks` (phase 2,
Step 10) names neither an OD nor a CQ, so it needs no `rejected`.

**Owner.** Each finding's `owner` is `orchestrator` when its subject line is either of these. Every
other finding is `architect`:
- an SD entry whose `source` is `user`, `user-edit`, `user-menu`, `user-override`, `materializer` or
  `implementation`
- any line in Research Requirements

For `duplicate-id`, the owner is that of the second definition's line. For example, a duplicate RP
belongs to the orchestrator, and a duplicate OD or FLOW belongs to the architect (judgment call 8).

**Accepted findings** (`drop_accepted_findings`). `PhaseTools.validate` passes both finding lists
through it, so the gate, the architect's self-check and the critic all see the same filtered result:
- **The finding key** is `<check> <subject>`, followed by a space and `[<part>]` when `part` is
  non-empty. For example, `decision-entry-malformed OD-003 [Option B]`. Including `part` means
  accepting one defect never hides a different defect on the same subject.
- **The match.** A finding is dropped when some SD entry has `source=user` and
  `supersedes=unresolved-checks`, read by the segment rules above, and contains the finding key
  anywhere in its line. The gate and the critic record findings as `<finding key> — <detail>` (work
  items 7 and 9), and phase 2 records each accepted finding verbatim.
- **The record.** Each dropped finding is returned as `accepted: <finding key>`, and
  `PhaseTools.validate` adds that line to `skipped_checks`.
- **Scope.** This applies to `structural_findings` and `implementation_findings` alike (B17).

**ID integrity.**

| Family | Defined by | Also resolves through |
|---|---|---|
| OD | a column-0 `- OD-<n> \|` entry in Open Design Decisions | any SD's `supersedes=OD-<n>` |
| SD | a column-0 `- SD-<n> \|` entry in Settled Design Decisions | — |
| CQ | never defined in the document; CQ IDs live only in the critic's report | any SD's `supersedes=CQ-<n>` |
| FLOW | a `- FLOW-<n>:` bullet in Design Shape - Additional Sections (the UX Contract) | any other FLOW-led bullet (see "Further readings": only the flow list counts toward duplicates) |
| RP | a bullet in Research Requirements, at any indentation, other than a `- Read:` line or a nested `- Applied:` line, whose first ID token is `RP-<n>`. Approval marks may sit anywhere on the line; README "Research recording" does not fix their position. | the RP IDs on a `- Read:` or `- Applied:` line (they resolve references but are never a definition, so never a duplicate) |

- **A reference** is any other match of `\b(OD|SD|CQ|RP)-\d+\b` or `\bFLOW-\d+\b`.
- **Exempt:** the defining token itself, the value of a `supersedes=` segment, and every token inside
  an SD entry or a Research Requirements line. Those lines are orchestrator-owned history (judgment
  call 1). Their IDs still count as **definitions** for resolving references elsewhere.
- **Fenced blocks** are skipped, both for definitions and for references.
- **Numbers compare as integers.**

**Cited paths** (`extract_cited_paths`). Existence is never checked. Each (`path`, `kind`, `cited_in`)
triple is returned once:
- `read`: every `- Read:` line in Research Requirements, at any indentation. The path is the first
  backticked span, or else the text after `Read:` up to ` — `.
- `constraint`: every `- Constraint:` line in Implementation Plan References. The path is the first
  backticked span, with any `§` qualifier (and the space before it) removed.
- `best-practices`: every other `.best-practices/…md` mention anywhere in `build_markdown()` except
  `### Settled Design Decisions`. A mention is a run of characters, other than whitespace,
  backticks, quotes, brackets and parentheses, that starts with `.best-practices/` and ends in
  `.md`. A path that a `- Read:` line already returned as `read` is not returned again for the same
  line.
- **Settled Design Decisions are never scanned for cited paths** (review fix, 2026-11-16). They are
  orchestrator-written history the architect carries forward verbatim, the same reason their
  references are exempt. An accept-as-is SD quotes the missing-path blocker it accepts, so scanning
  it would turn the accepted `read` path into a new `best-practices` entry under a different
  critic marker, which the architect cannot remove and which reaches the user again (judgment
  call 9). Trade-off: an architect-sourced SD that cites a missing path goes unchecked.

These are respec-ai's own document grammar, not a target language. The critic picks its marker by
`kind` (work item 9).

**`implementation.md` checks** (`check_implementation_structure`). These run line by line and are
fence-aware. They match H2 and H3 names exactly; this is new code, so it has no substring trap. They
cover only the fields that exist today (README "Frozen-reader compatibility"; F33).

| `check` | Fires when |
|---|---|
| `implementation-section-missing` | Any of `## Build Order > ### Steps`, `## Checklist` or `## Policy` is absent. `part` names it. |
| `implementation-step-heading-malformed` | A `####` heading under Steps is not `#### Step <integer>: <non-empty title>`. Readers scan exactly that form (`code_command.py:291`; the test-side mirror is `tests/support/plan_extraction.py:13`). |
| `implementation-no-steps` | Steps holds no valid step. |
| `duplicate-id` | The same step number is defined twice. |
| `implementation-checklist-item-malformed` | A `- [ ]`, `- [x]` or `- [X]` item under `## Checklist` lacks `(Step <integer>)` (`part`: `step`), or has no `(verify: …)` group (`part`: `verify`). Each group runs from `(verify:` to its balanced `)`; an item may carry one group per language (phase 1, item 7). Also fires (`part`: `verify`) when a group's command is empty; starts with `TODO` in any case, optionally bracketed; is `no_preference` (F25); or is wholly a `<…>` or `[…]` placeholder. A command starting `ask user` is phase 1's sanctioned marker and passes (judgment call 1). |
| `dangling-reference` | A `(Step N)` names no step, or an OD, SD, CQ, FLOW or RP ID is undefined in the phase, resolved exactly as above. |
| `implementation-step-unverified` | A step is named by no checklist item, so nothing verifies it. |

Every `implementation.md` finding has `owner: architect`, because the architect writes the file.

**Subjects and parts where the tables are silent** (pinned by `tests/unit/utils/test_phase_structure.py`
in stage S1, choosing the fewest-findings reading per judgment calls 1 and 6). They feed the finding
keys the gate, the critic and accept-as-is SDs quote:
- **Line subjects.** `seam-entry-malformed`, `seam-signature-unparseable`,
  `test-entry-without-behavior`, `implementation-step-heading-malformed` and
  `implementation-checklist-item-malformed` use the offending line, stripped. An OD bullet with no
  ID (`part`: `entry line`) and an unnumbered `SD-###` entry also use the stripped line.
- **Path and ID subjects.** `seam-path-not-in-module-layout` uses the path as written.
  `duplicate-id` uses the second definition's ID as written (`OD-003` after `OD-3`), and its owner
  is that line's. `settled-decision-still-open` uses the OD ID as written under Open.
  `dangling-reference` uses the ID as written. Step references use `Step <N>` for
  `dangling-reference`, `duplicate-id` and `implementation-step-unverified`.
- **Section subjects.** `test-list-empty` uses `Test List`, and also fires when the Test List is
  absent. `implementation-no-steps` uses `Steps`. `implementation-section-missing` uses
  `implementation.md`, with `part` `Build Order > Steps`, `Checklist` or `Policy`.
  `section-name-overlap` uses the H2 name with an empty `part`; both names of an overlapping pair of
  unmapped H2s are reported.
- **One finding per fix.** The retired single-line OD form yields only `single-line form`, not also
  missing `Option A`, `Option B` or `Recommended`. A missing Steps section suppresses
  `implementation-no-steps`, and a missing Checklist suppresses `implementation-step-unverified`.
  A `#### Step 3:` heading with an empty title yields only the malformed-heading finding.
  A Recommended that names a missing `Option A` or `Option B` yields only that option's finding:
  restoring the option is the fix, and a `Recommended` finding would push the architect to change
  the recommendation instead (stage S2).
- **SD parts** are the missing field's key, or `source`.
- **`cited_in`** is `<H2> > <H3>` for a typed field, or the bare name of an unmapped H2.
- **Definitions are section-scoped.** Parsing copies a captured section's text into an
  overlapping unmapped H2 (F27 trap 1: `## Design` captures `## Design Shape`), so count
  definitions only in their own typed fields, or the copy raises a false `duplicate-id`.

**Further readings fixed in stage S2** (the same fewest-findings rule; each is pinned by a test in
`tests/unit/utils/test_phase_structure.py`):
- **References the architect cannot repair are not scanned.**
  - The frozen Overview fields (`FROZEN_PHASES_FIELDS`, `src/utils/state_manager/base.py`) are
    exempt. Storage preserves them over any `update_document`, so no repair round could fix a
    reference there.
  - Every line of `### Settled Design Decisions` is exempt, not only lines shaped like an SD entry.
  - An additional section reported by `section-name-overlap` is not scanned for references. Its
    text may be a copy of the section that captured it, and the overlap finding already names
    the one fix.
- **Settlement comes from the parsed `supersedes=` value only.** An OD or CQ token quoted anywhere
  else on an SD line (for example inside an accept-as-is SD's `decision=`) settles nothing.
- **Definitions are lenient about the line around the ID.** A column-0 bullet whose first token is
  `OD-<n>` defines that OD whatever follows it; a separator other than `|` is still reported as
  `entry line`. A bullet at any indentation whose first token is `FLOW-<n>` resolves references to
  that flow. Only the flow list counts toward `duplicate-id` (review fix, 2026-11-16): a column-0
  FLOW-led bullet inside `##### Interaction Flows`, or anywhere in the section when the UX Contract
  has no such subsection. Indented FLOW-led bullets, and FLOW-led bullets under other subsections
  (per-flow keyboard paths, breakpoint notes), restate a flow; counting them raised a duplicate
  whose suggested renumbering would corrupt the contract. They still resolve, so an indented flow
  definition never dangles. Bold markers (`**`) are ignored on FLOW, Option and Recommended lines.
- **OD sub-lines.** The option letter may be followed by `:`, `.`, `)` or a dash. The
  `Recommended` separator is optional.
- **Module Layout.** A Module Layout entry covers every path below it whether or not it was written
  with a trailing `/`; comparison drops a leading `./` and any trailing `/`. When Module Layout
  yields no backticked bullet path at all, `seam-path-not-in-module-layout` does not fire. The path
  check covers every backticked `` `<path>` :: `` line at any indentation, because the CLI reads
  those too.
- **Test List.** The `<path>::<behavior>` span must open the bullet: the promoted bullet grammar,
  the same one the CLI reads. A bullet whose first backticked span sits later on the line is a
  defect. A bullet at any indentation counts toward a non-empty Test List.
- **`- None`** matches case-insensitively when `None` is the bullet's first word. A source matches
  case-insensitively.
- **Checklist.**
  - Items at any indentation count, both for validation and for the steps they verify.
  - A `(verify:` with no balanced `)` is no group, so it gets the `verify` finding.
  - A `dangling-reference` to `(Step <N>)` is not reported when Steps holds no valid step. A
    malformed heading that still reads `#### Step <N>` registers `N`, so an item naming it is not
    also dangling.
  - `implementation-no-steps` is not reported when any step heading is malformed.
- **Duplicate findings collapse.** Findings with the same finding key are reported once, at the
  first location.
- **Accepted-finding match.** The key is matched as plain text, and must be followed by whitespace
  or the end of the SD line. So accepting `dangling-reference OD-12` never hides
  `dangling-reference OD-1`, and accepting a path never hides a finding on a path that is a prefix
  of it.
- **Fences.** A fence opens on a line whose first non-space characters are three or more
  backticks with no backtick after the run, or three or more tildes (CommonMark's info-string
  rule; review fix, 2026-11-16). So a line like ```` ```x``` notes ```` is inline code and hides
  nothing. Indentation is not limited, so a fence inside a list item still hides its lines.
  Fenced lines are skipped everywhere except the Skeleton Index and the Test List: their CLI
  readers strip each line and never skip fences, so a fenced line the CLI reads (a backticked
  seam with ` :: `, or a backticked span containing `::`) is checked exactly like an unfenced one,
  and a valid fenced seam or test entry counts as present. Other fenced lines there stay unreported,
  because the CLI ignores them too (B2 parity without flagging fenced examples).
- **Cited paths.**
  - Fenced lines are skipped.
  - Settled Design Decisions are skipped (see `best-practices` above).
  - A best-practices mention is cut from runs delimited by whitespace, backticks, straight and
    typographic quotes, brackets, braces and parentheses. Only a run that starts with
    `.best-practices/` counts, so `docs/.best-practices/x.md` is not a mention.
  - The mention ends at the run's last `.md` that no word character or hyphen follows. Trailing
    punctuation is dropped, and `.mdx` is not a mention.
  - A `- Constraint:` line's own path is not also returned as `best-practices`.
- **Never raise.** ID and step numbers compare as digit strings with leading zeros stripped, never
  through `int()`, which refuses runs over 4300 digits. Verify groups are balanced with an
  iterative counter.
- **Details never interpolate document text.** A `detail` names paths, lines, signatures and H2
  names only as "this path", "this entry" or "this item", because real paths carry extensions
  (judgment call 6); `subject` carries the verbatim text. IDs, `Step <N>` and known `source`
  values are interpolated.
- **A `*` or `+` marker gets its own detail** (review fix, 2026-11-16). The CLI reads only `-`
  bullets, so a Skeleton Index or Test List line that would be a valid entry with a `-` marker is
  told to start with `-`, not to add backticks it already has. `check`, `subject` and `part` are
  unchanged.

#### 3. `PhaseTools.validate` and the tool interface

- **`DocumentToolsInterface.validate`** (`src/mcp/tools/base.py:30-38`; `:16-22` before stage S3):
  - **Signature:** `validate(content: str | None = None, key: str | None = None,
    implementation_markdown: str | None = None) -> DocumentValidationResponse`.
  - **The base implementation** keeps today's content-loss behavior, using `content` only. It raises
    `ToolError` when given `key` or `implementation_markdown`: only phase documents support them.
- **`PhaseTools.validate`** is a new override in `src/mcp/tools/phase_tools.py`, inside the class at
  `src/mcp/tools/phase_tools.py:106-107` (`:24-25` before stage S3), satisfying the probe (`:109`).
  - **Exactly one input.** Exactly one of `content` and `key` is required; otherwise `ToolError`.
  - **`content`:**
    - It runs `Phase.find_content_loss` (work item 4) for `status` and `message`, exactly as today.
    - It then attempts `Phase.parse_markdown`.
    - **On `ValueError` or `ValidationError`**, it adds `The document cannot be stored: <reason>` to the
      content-loss lines, sets `status` to `user_input`, and records
      `structure: document does not parse` in `skipped_checks` (B11).
  - **`key`:**
    - It loads the stored phase through `_parse_key` (`src/mcp/tools/phase_tools.py:276-280`) and
      `self.state.get_phase`, mapping `PhaseNotFoundError` to `ResourceError` as
      `src/mcp/tools/phase_tools.py:200-201` does.
    - Content loss is not meaningful on rebuilt markdown, so `status` is `completed`, and `message`
      says that content loss is not checked in key mode.
  - **Both modes** set:
    - `structural_findings` from `check_phase_structure`
    - `paths_to_verify` from `extract_cited_paths`
    - `implementation_findings` when `implementation_markdown` is given; otherwise
      `skipped_checks` gets `implementation.md: not passed`
    - both finding lists passed through `drop_accepted_findings`, with its `accepted: …` lines added
      to `skipped_checks`
    - `skipped_checks` always gets
      `cited-paths-exist: the server cannot see the project filesystem; verify paths_to_verify on the host`
- **`DocumentTools.validate_document`** (`src/mcp/tools/document_tools.py:38-52`; `:38-46` before
  stage S3) forwards all three inputs. Its "content cannot be empty" guard (`:39-40` before stage S3)
  became the exactly-one rule (`:45-46`).
  - The new signature is `validate_document(self, doc_type, content: str | None = None,
    key: str | None = None, implementation_markdown: str | None = None)`.
  - `content` stays the second positional parameter, because the existing tests in
    `tests/unit/mcp/test_document_validation.py` pass it positionally.
- **The registered tool** (`document_tools.py:149-195`; `:143-167` before stage S3):
  - It gains `key` and `implementation_markdown`, and `content` becomes optional.
  - Write all three as `str | None = None`, after `ctx: Context`, the way `get_document` orders
    `include_phases` (`document_tools.py:198-203`). fastmcp marks a `str | None` parameter with no
    default as required; the probe confirmed that `doc_type` is then the only required input.
  - Its return annotation becomes `DocumentValidationResponse`, so the published `output_schema` is
    truthful (B14).
  - **Rewrite the docstring** (`:157-187`; `:145-159` before stage S3). Agents read it as the tool
    description. It must state:
    - the two modes
    - that `status` reports content loss only
    - what each result field holds
    - that file existence is never checked server-side

    It names no language (B9).

**Readings fixed in stage S3.** `tests/unit/mcp/test_document_validation.py` pins the behaviors
(which inputs count as passed, what is skipped and when); the exact wording, the `id` values and
the `skipped_checks` order are implemented but unpinned:
- **Empty strings.** For the exactly-one rule, an empty `content` or `key` counts as absent, as the
  old "content cannot be empty" guard did. `implementation_markdown` counts as passed whenever it is
  not `None`, so an empty body is checked and reports its missing sections.
- **The unstorable line** is `- The document cannot be stored: <reason>` under a
  `Content loss detected:` header, after any heading lines. `UNSTORABLE_DOCUMENT` (`'The document cannot be stored'`) is a
  constant in `src/models/document_validation.py`, beside `CONTENT_LOSS_WARNING`; work item 7's
  hand-edit menu imports it rather than retyping it. The reason is one line: a `ValidationError`
  becomes `<field>: <message>` pairs joined by a semicolon and a space.
- **When the content does not parse,** `skipped_checks` holds `structure: document does not parse`,
  then `implementation.md: not passed` (or, when a body was passed,
  `implementation.md: not checked, because the phase document does not parse`), then the
  `cited-paths-exist` line. The structural lists and `paths_to_verify` are empty.
- **`skipped_checks` order** otherwise: `implementation.md: not passed` when no body was passed,
  then the `accepted: …` lines (structural, then implementation), then the `cited-paths-exist` line.
- **Key mode** returns `id` = the key and `message` =
  `Content loss is not checked in key mode: the stored phase has already been parsed.` Content mode
  keeps `id` = `validate`.

#### 4. Content loss covers additional sections

A `find_content_loss` classmethod override on `Phase` (`src/models/phase.py:99-120`) calls `super()`
(base implementation at `src/models/base.py:219-240`; `:201-221` before stage S3) and adds:

- **Unmapped H2 truncation and capture.** For each unmapped H2, enumerated the way `parse_markdown`
  does (stage S3 moved that enumeration into `MCPModel._unmapped_h2_headings`,
  `src/models/base.py:241-251`, which `parse_markdown` now calls at `:429-434`), it compares
  `_extract_raw_section_verbatim` (`src/models/base.py:150-191`) against
  `_extract_content_from_raw_markdown` (`src/models/base.py:73-126`). Any difference is loss. This catches the bare-`---` case and the
  capture-by-substring case.
- **Heading lines inside a fence.** A fence-aware line scan of ```` ``` ```` and `~~~` blocks flags:
  - any `##` heading line inside a fence, wherever it sits
  - a `###` heading line inside a fence only when the enclosing real H2 is mapped, whatever the fenced
    heading's name
  - Both raw extractors stop at such a line and drop the rest of the section. The verbatim extractor
    stops there too, so the comparison cannot see it (probe above).
  - Do **not** flag a fenced `###` heading line under an unmapped H2. Nothing is lost there, and a false
    report would put a phantom problem in the user's hand-edit menu.
  - Report one line per affected heading, in the base implementation's `<heading path>: …` style.
    Do not repeat a heading that `super()` already reported.

It goes on `Phase`, not `MCPModel`: only phase validation has a consumer (F29), and
`test_content_loss_detection.py:24-35` runs over Plan and Roadmap too.

Also confirm that both existing guards stay green: "a document this system generates never reports
content loss" (`:24-31`) and "the shipped phase template never reports content loss" (`:34-35`). The
second one's import at `:21` must point at the architect's constant (Start here, prerequisites).

Do not repair the parser traps themselves. This phase detects; it does not change parsing, the same
stance phase-refactor took (`src/models/base.py:221-226`).

**Readings fixed in stage S3.** `tests/unit/models/test_content_loss_detection.py` pins which
headings are reported, the column-0 rule, the unclosed-fence collapse and the two-line orphan case;
the line wording, the `Before the first section` name and the probe result are unpinned:
- **Fence spans come from markdown-it,** the parser `parse_markdown` already uses: the lines inside
  each `fence` node's `map`, closing line included. A line counts only when it starts at column 0
  with a `##` or `###` heading marker and a space, exactly what the raw extractors stop on, so an indented heading-like line
  in a list-item fence cuts nothing and is not reported. An unclosed fence runs to the end of the
  document, as CommonMark reads it.
- **The affected heading** is the enclosing real section: `<H2> > <H3>` under a mapped H2, the bare
  H2 name under an unmapped one (its H3s are content), or `Before the first section` when no real
  H2 precedes the fence. Each heading is reported once, whatever mix of fenced lines and a bare
  `---` cut it, and an unclosed fence that swallows later headings yields that one line.
- **Lines** read `<heading>: <reason>`. Truncation reuses the base wording (`CONTENT_TRUNCATED`,
  `src/models/base.py:11`); a fenced heading line reads `a line inside a fenced block, or after a
  fence that is never closed, starts like a heading, so storing ends this section at that line and
  loses the text after it`.
- **A fenced `###` line with an unmapped name under a mapped H2** yields two lines: the base orphan
  line for the fenced name, and this check's line for the enclosing H3, which is genuinely cut
  short. They name different headings, so neither repeats the other.
- **An unmapped H2 placed before the H2 whose name contains it** loses nothing and is not reported
  as content loss; `section-name-overlap` reports it as a structural finding.
- **False-positive probe.** On 2026-11-16 the override added no line to the base report for any of
  the 30 real `phase.md` files under `~/code/*/.respec-ai` (read only).

#### 5. Agent writes report their own content loss

`PhaseTools.update` (`src/mcp/tools/phase_tools.py:307-325`; `:192-208` before stage S3):
- runs `Phase.find_content_loss(content)` before parsing
- when it finds loss, appends a line starting with `CONTENT_LOSS_WARNING` that lists the headings to
  the response message, mirroring `with_discard_warning` (`:28-37`, applied at `:320`). The line
  is `WARNING: content lost on write (<line>; <line>). The phase was stored without this text.`,
  each `<line>` a whole `find_content_loss` line (`<heading>: <reason>`), so heading names that
  contain a colon stay intact
- stores exactly as before

**Why a warning, not a rejection.** Frozen respec-patch also writes phases through `update_document`
(`create_patch_command_tools`, `src/platform/template_helpers.py:1653-1658`, rendered at
`src/platform/templates/commands/patch_command.py:1137`), and a rejection would break it.
Create-phase holds the `update_document` grant (`src/platform/models/roadmap.py:109-114`), but its
template writes through `store_document` (`src/platform/templates/agents/create_phase.py:121`), so it
is unaffected either way.

**Why not a pre-write validate.** It would make the architect emit a 20–40KB document twice on every
write, and a model can skip a step; it cannot skip a tool result.

Only the agent path changes. `store_document` is untouched (Out of scope).

### Part B — wiring (needs phase 2)

#### 6. Tool grants and rendered calls

- **The architect** (`PhaseArchitectAgentTools`, `src/platform/models/phase.py:144`; builder
  `create_phase_architect_agent_tools`, `src/platform/template_helpers.py:805`):
  - add `RespecAITool.VALIDATE_DOCUMENT` to `respec_ai_tools` (`:151`)
  - add a `validate_document` field (`:169`) rendered as
    `validate_document(doc_type="phase", key={PLAN_NAME}/{PHASE_NAME}, implementation_markdown={IMPLEMENTATION_PLAN_MARKDOWN})`
- **The critic** (`PhaseCriticAgentTools`, `src/platform/models/phase.py:174`, grant at `:179`,
  field at `:193`; builder `create_phase_critic_agent_tools`, `src/platform/template_helpers.py:846`):
  the same grant and field. It stores nothing, so the critic stays read-only.
- **The orchestrator** (`PhaseCommandTools`, `src/platform/models/phase.py:14`, already granted at
  `:20`): add a `validate_document_structure` field (`:59`) next to today's content-mode
  `validate_document` (`:58`; rendered at `src/platform/template_helpers.py:315`). Render it as
  `validate_document(doc_type="phase", key={PLAN_NAME}/{PHASE_NAME})` (`:318`), with the `key`
  value written as `store_document_user_edit` writes it (`:321`; it was `store_document_gate_edit`
  before phase 2). The name follows phase 2's `verb_object_qualifier` fields. Keep the content-mode
  field as it is.

**Landed in stage S4.**
- **Placeholder corrected.** The agents' variable is `IMPLEMENTATION_PLAN_MARKDOWN` (both
  templates already used it), so the field renders `{IMPLEMENTATION_PLAN_MARKDOWN}`, not the
  `{IMPLEMENTATION_MARKDOWN}` this item first named. One helper,
  `_render_phase_structure_validation` (`src/platform/template_helpers.py:796`), renders it for
  both agents.

#### 7. The orchestrator gate

This goes in phase 2's rewritten `src/platform/templates/commands/phase_command.py`.
- **Where.** At the top of phase 2's Step 9 ("Critic Review and Automatic Repair"), before
  `REVIEW_ROUND += 1` and the critic invocation. Every path into Step 9 passes this point, so the
  gate follows every architect `draft` or `revise` and every stored hand edit with no second copy:
  - Step 8's draft
  - Step 9's own `refine` or `user_input` repair
  - every Step 10 send-back: a change request, a hand edit (including its abort), a
    design-changing answer, a relayed question that persisted something, and Step 7's follow-up
  - Step 11's design-changing answers, which follow Step 10's rule
  - Step 4's resume and re-open routes

  ```text
  STRUCTURAL_LEFTOVERS = []
  VALIDATION = {tools.validate_document_structure}
  ARCHITECT_FINDINGS = VALIDATION.structural_findings whose owner is "architect"
  ORCHESTRATOR_FINDINGS = VALIDATION.structural_findings whose owner is "orchestrator"
  IF ARCHITECT_FINDINGS is not empty AND REPAIR_ROUNDS < 2:
    REPAIR_ROUNDS += 1
    <re-engage the architect in revise with phase 2's resume-or-fresh expression>
    Return to the top of Step 9.
  STRUCTURAL_LEFTOVERS = each finding in ARCHITECT_FINDINGS and ORCHESTRATOR_FINDINGS,
    written as "<check> <subject> — <detail>", or "<check> <subject> [<part>] — <detail>"
    when part is non-empty
  ```

  - The re-engage is phase 2's single re-engagement rule ("Re-engaging the architect (every
    site)"): set `ARCHITECT_MODE = "revise"`, then use `{tools.resume_architect}` when it is
    non-empty and `ARCHITECT_AGENT_ID` is set, falling back to `{tools.invoke_architect_revise}`.
    Phase 2 defines one `resume_architect` field for every mode; there is no per-mode resume field.
    It is not a bare fresh invocation, and Step 9's own repair uses the same rule.
  - The repair branch contains no `WAIT for` and no selection prompt (B15).
- **The budget.**
  - `REPAIR_ROUNDS` is phase 2's two-round budget (README "Critic findings"; phase 2 Step 9),
    **shared** with critic `[mechanical]` findings. Phase 2's Step 3 initializes it to 0.
  - It resets each time Step 10 sends work back to Step 9, whichever send-back it is (phase 2,
    Step 9).
  - Orchestrator-owned findings never spend a round (judgment call 8).
- **Leftovers reach the user once.**
  - Change phase 2's Step 9 branches so that `UNRESOLVED_CHECKS` = `STRUCTURAL_LEFTOVERS` + the
    latest `### Blockers` whenever it is set. A `completed` decision with non-empty
    `STRUCTURAL_LEFTOVERS` also sets `UNRESOLVED_CHECKS = STRUCTURAL_LEFTOVERS` before going to
    Step 10. Never replace leftovers with the blockers alone.
  - The critic still runs once after the budget is spent, so its judgment questions are asked.
  - Record each structural leftover in the accept-as-is SD exactly as written above, so that
    `drop_accepted_findings` matches its finding key on every later round (B17).
- **Write `structural_findings` literally in the template text.** The wiring probe greps for it.
- **The hand-edit path** keeps branching on `status` from its content-mode call, exactly as today.
  It ignores that call's structural fields. The gate at the top of Step 9, which runs after the edit
  is stored, is their only source.
- **An unstorable edit has two exits, not three.** When a content-loss line reads `The document cannot
  be stored: …` (B11), the hand-edit menu offers only fix-and-retry or abort. Today's "Drop those
  edits and continue" (`phase_command.py:720`, branch at `:737`, pre-phase-2) passes the raw text on
  to `store_document`, which raises on exactly this case. Whatever form phase 2 gives that menu,
  either withhold that option here or make it mean "discard the whole edit and keep the stored
  version".
- **If phase 2 fell back** to the orchestrator writing `implementation.md` from the report, pass
  `implementation_markdown` in the gate call and treat `implementation_findings` like
  `structural_findings`. It did not: the architect writes the file, so the gate passes no body.

**Landed in stage S4** (`src/platform/templates/commands/phase_command.py`):
- **The gate** sits at the top of Step 9 (`:853`), before `PRE_PHASE_LOOP_STATUS`,
  `REVIEW_ROUND += 1` and the critic: `VALIDATION` at `:864`, the owner split at `:867-868`, the
  repair branch at `:872`, `STRUCTURAL_LEFTOVERS` at `:878`. The repair branch reuses phase 2's
  rendered `revise` engagement unchanged (resume behind `ARCHITECT_AGENT_ID` on Claude Code, a
  fresh invocation otherwise), then returns to the top of Step 9.
- **Leftovers.** `completed` sets `UNRESOLVED_CHECKS = STRUCTURAL_LEFTOVERS` when it is non-empty
  (`:919-920`); both spent-budget branches set `STRUCTURAL_LEFTOVERS` + the latest blockers
  (`:929`, `:940`). The accept-as-is SD now says to quote each finding exactly as
  `UNRESOLVED_CHECKS` holds it, all on the SD's one line joined by a semicolon and a space (`:1058-1060`).
  `drop_accepted_findings` reads only an SD's own line, so a finding wrapped onto a continuation
  line would be asked again; `test_every_leftover_quoted_on_the_one_accept_line_stays_accepted`
  pins why.
- **The budget reset.** Phase 2 resets `REPAIR_ROUNDS` once, at the top of Step 10.1 (`:957`),
  which every send-back passes. That is equivalent to "each time Step 10 sends work back", so it
  is unchanged; Step 9 never resets it (B15 pins that).
- **Step 10.2 wording.** The unresolved-checks prompt no longer says "the critic's checks" or
  "after two automatic repairs": orchestrator-owned findings arrive with no repair at all. Prompt
  wording is not test-pinned.
- **Answered once** (review fix, 2026-11-16). Step 10.2 sets `UNRESOLVED_CHECKS = []` right after
  recording either answer. Sign-off's "Go back to design review" re-enters Step 10 without passing
  Step 9, the only other reset, so without it an accepted finding was asked again and recorded in a
  second accept SD. `test_answering_the_unresolved_checks_clears_them_so_no_return_to_design_review_asks_again`
  pins it on all three TUIs.
- **The unstorable edit.** Step 10.5 (`:1127`) withholds "Drop those edits and continue": when a
  content-loss line reads `UNSTORABLE_DOCUMENT` (imported, `:3`; the guard at `:1141`), the menu
  offers only "Let me fix it and try again" and "Abort and send it back to the architect", each
  with its own `WAIT for` and resume marker. The three-option menu stays for storable loss.

#### 8. The architect

This goes in phase 2's rewritten `src/platform/templates/agents/phase_architect.py`, in `draft` and
`revise`.
- **After each `update_document`:** if the response contains `CONTENT_LOSS_WARNING` (imported, not
  retyped), rewrite the named headings and update again.
- **Before returning:**
  - Call `validate_document` in key mode, passing the body of the `implementation.md` it wrote as
    `implementation_markdown`.
  - Fix every finding whose `owner` is `architect`. Leave `orchestrator` findings untouched: the
    lines they name are preserved verbatim.
  - Glob every `paths_to_verify` entry, and fix or remove any citation of a file that does not exist.
    This applies only to citations in architect-owned text; ledger lines are the orchestrator's.
  - Repeat until clean, at most twice. The gate is the authority, not this self-check.
- **Never skip the self-check.** A `revise` whose `get_feedback` holds nothing new is a structural
  repair round, invoked by the gate with IDs only. It still runs the steps above, and it must not
  return early with "no new feedback".
- **The constraints from judgment call 5 apply.** A finding it cannot fix without contradicting a
  user entry stays unfixed and is named in `## For the user`, not in `## Decisions needed`.

**Landed in stage S4** (`src/platform/templates/agents/phase_architect.py`):
- `CONTENT_LOSS_WARNING` is imported (`:3`) and checked after STEP 4's `update_document` (`:655`)
  and after the self-check's (`:691`). The shared `CONTENT LOSS ON WRITE` rule (`:661`) names the
  three parser traps to avoid. **Not in the spec, decided here:** when two rewrites still warn,
  the architect names the headings in `## For the user` instead of looping.
- The self-check is `STEP 4.5` (`:667`), after STEP 4 persists the document and `implementation.md`
  and before the notes are stored. It is guarded only by `phase_mode` draft or revise, never by
  feedback newness, and re-reads `implementation.md` from disk when the engagement did not write
  it. It validates, Globs each `paths_to_verify` entry outside the ledger's RP and `- Read:` lines
  and the frozen `## Overview` (storage preserves the Overview, so no fix there survives), fixes,
  persists, and repeats, with at most two fix passes.
- The revise branch says that when STEP 2 finds nothing new the engagement is a structural repair
  round (`:573-574`).

#### 9. The critic

This goes in phase 2's rewritten `src/platform/templates/agents/phase_critic.py`. Rules are located
by marker; the origins below are as of 2026-11-13, pre-phase-2.

- **Remove the moved rules**, in whatever form phase 2 left them:
  - `Malformed Decision Entry` (origin `phase_critic.py:290-297`)
  - `Empty Test List` and `Test List Names File Not Behavior` (`:1131-1138`)
  - `Skeleton Index Module Mismatch` (`:1140-1143`)
  - **The presence half of phase 2's new Checklist check** (phase 2, work item 4, "Add": every
    Checklist item carries `(Step N)` and a `(verify: …)`). `implementation-checklist-item-malformed`
    now covers presence. The critic keeps only the half the server cannot do: each verify command
    matches the owning language's `[commands].test` in `project_config_context_markdown`, or the
    command a `source=user` SD records for that language (phase 2's missing-verify-command
    decision, Option B), or is phase 1's `ask user` marker.
- **Re-source the existence checks.** `Research Path Invalid`, `Best-Practices Reference Invalid` and
  `Implementation Plan Reference Invalid` stay as markers. Their path lists now come from
  `paths_to_verify`, and the marker is chosen by `kind`: `read` → Research Path Invalid,
  `best-practices` → Best-Practices Reference Invalid, `constraint` → Implementation Plan Reference
  Invalid. Each missing path raises exactly one marker.
  - **Known residual.** A missing `read` path sits on a ledger line the architect cannot repair, so
    that blocker spends the repair budget before it reaches the user. It is rare, because the
    orchestrator writes `- Read:` lines only after confirming the file exists. Do not reclassify it
    here; the classification is phase 2's (its work item 4 table).
  - The prompt-encoded extraction that phase 2 kept is replaced:
    - the `- Read:` parser (origin `phase_critic.py:540-583`)
    - the `.best-practices/` mention scan (`phase_critic.py:616-617`)
    - the `- Constraint:` extraction (`phase_critic.py:778-783`)
- **Relay implementation findings.** Each `implementation_findings` entry becomes
  `[mechanical] [Implementation Plan Structure Invalid - BLOCKING]: <check> <subject> — <detail>`,
  with a space and `[<part>]` after `<subject>` when `part` is non-empty. That finding key is what
  `drop_accepted_findings` matches once the user accepts it (B17), so write it exactly.
- **Never re-raise `structural_findings`.**
- **Keep** the judgment rules: Unjustified Seam, Under-Surfaced Decision, Non-Divergent Options,
  Implementation Plan Reference Not Applied and Plan Constraint Violation.
- **Keep** the mechanical rules this phase does not move:
  - the UX Contract rules
  - the frontend presence classes
  - phase 2's "every step names the files it touches" and "every Test List entry is covered by some
    step" (see Out of scope)
- **Test fates:**
  - `tests/unit/templates/test_agent_templates.py:618-626` (`test_shape_mode_enforces_od_entry_format`)
    asserts the `Malformed Decision Entry` string in the critic. Delete that test; B4 carries its
    intent server-side.
  - This is a sequence, not a conflict: phase 2 keeps the test, and this phase deletes it. F36 and
    phase 2's work item 8 row for `:618` both already say so.
  - `test_agent_templates.py:474-485` (`test_template_treats_best_practices_paths_as_blocking_verification`)
    pins the existence-check markers that survive here. Keep its `Research Path Invalid` and
    `Best-Practices Reference Invalid` assertions. Drop its `'.best-practices/*.md' in template`
    assertion: that scan moves into `extract_cited_paths`, and B7 pins it.

**Landed in stage S4** (`src/platform/templates/agents/phase_critic.py`):
- **Test fates, located by name.** Phase 2 renamed `test_shape_mode_enforces_od_entry_format` to
  `test_malformed_decision_entry_is_a_mechanical_blocker_in_review`; that test is deleted.
  `test_template_treats_best_practices_paths_as_blocking_verification` (`test_agent_templates.py:486`)
  lost only its `'.best-practices/*.md'` assertion. A third phase 2 test pinned the presence half
  this item moves: `test_critic_raises_implementation_plan_defects_as_mechanical_findings` (`:613`)
  no longer expects `step-without-verify-command` or `checklist-item-malformed`, and now expects
  `implementation-plan-structure-invalid`.
- **The presence half** was phase 2's two markers `Step Without Verify Command` and
  `Checklist Item Malformed`; both are gone. "One `(verify: …)` per language whose files the step
  touches" is not a presence check the server can make, so it moved into `Verify Command Not
  Configured` (`:452`), whose finding now reads "has no configured, user-recorded or ask-user
  verify command for `<language>`".
- **Examples.** `Skeleton Index Module Mismatch` also sat in the classification example and in
  `phase_feedback_template`'s blockers; both now show kept markers, the latter a concrete
  `Implementation Plan Structure Invalid` relay (`:38`).
- **Where.** The critic validates in a new `STEP 5.5` (`:237`), after reading `implementation.md`.
  When that Read fails it leaves `implementation_markdown` out; an empty body would report three
  missing sections next to `Implementation Plan Missing`. The structural rules are named as not
  raised at `:338`. `### Cited Paths` (`:282`) replaces the three prompt-encoded extractions, and
  the relay is `IMPLEMENTATION PLAN STRUCTURE` (`:443-447`).
- **Known residual, unchanged.** A best-practices path cited in the frozen Overview reaches
  `paths_to_verify` (stage S2), so a missing one is a blocker the architect cannot repair. It is
  the same class as the `read` residual above, and it is left for the user's unresolved-checks
  decision.

#### 10. Contract and index edits (same commit as the change they describe)

In `docs/phase-cooperative/README.md`:
- **Agents and modes table:** add `validate_document` to the architect's and the critic's
  "Granted, beyond today". The critic stays read-only.
- **Decision entry → "Validation":** `validate_document` now reports these defects, and Python parses
  these entries (F35's premise no longer holds).
- **Settled decision entry:**
  - Add the per-source required-field table from work item 2, including `materializer` and the
    legacy `user-menu`/`user-override` rows.
  - Add the segment rules: the first occurrence of a key wins, and any other segment, including a
    repeated key, continues the previous value.
  - State that an accept-as-is unresolved-checks SD quotes each structural or implementation finding
    as `<finding key> — <detail>`, and that the server stops reporting a finding so quoted. The
    finding key is `<check> <subject>`, plus a space and `[<part>]` when `part` is non-empty.
- **Critic findings → `[mechanical]` examples:**
  - The structural defects in work item 2 are detected by `validate_document` and repaired through
    the gate, never raised by the critic.
  - The critic still raises these mechanical findings: missing cited paths, the relayed
    `implementation.md` findings, the verify-command match against project config, the UX Contract
    rules, the frontend presence classes, phase 2's step-file and Test List coverage checks, and
    phase 4's cold-start check.
  - Structural repair rounds share the two-round budget. Orchestrator-owned findings skip it and go
    straight to the unresolved-checks decision.
- **Relay protocol step 5, hand edits:** structural findings go to the architect as a repair round,
  never to the user, unless they are orchestrator-owned or left over once the budget is spent.
- **Phase 3 probe:** the README already carries
  `grep -q "async def validate(" src/mcp/tools/phase_tools.py && grep -n "structural_findings" src/platform/templates/commands/phase_command.py`.
  Confirm it prints a match. The `-q` matters: the probe reads "output means done", and a printing
  first grep would produce output when only the MCP half had landed.

**Landed in stage S5 (2026-11-16).** Every edit above is in `README.md`:
- The agents table grants `validate_document` to the architect and the critic (the critic keeps no
  Write, Edit, `update_document` or `store_document`).
- "Validation" under the decision entry now says Python parses the entries.
- "Settled decision entry" carries the per-source table, the segment rules and the accept-SD
  quoting rule (one line, entries joined by a semicolon and a space, plus the `accepted: <finding key>` skip record).
- "Critic findings" names the structural defects as repaired through the gate and never raised, and
  states the shared budget and the orchestrator-owned exemption. Its tag example, formerly
  `Skeleton Index Module Mismatch`, is now `Verify Command Not Configured`.
- Relay protocol step 5 describes structural repair rounds.
- The "Pending amendments" paragraph records that phase 3's amendments landed.
- The README phase 3 probe prints a match (`phase_command.py:872-874`).

**Review fixes (2026-11-16).** After S5, reviewers confirmed defects that the amendments above
record in place (RP and FLOW definitions, fences, cited paths in Settled Design Decisions, the
`*`/`+` marker detail, the Step 10.2 reset). Four more need a note here:
- **"Critic findings" in `README.md`** no longer lists "a step without a verify command" among the
  defects the gate repairs. `implementation.md` defects come back as `implementation_findings`,
  which the gate never sees (it passes no body): the architect's self-check fixes them and the
  critic relays the rest.
- **Critic blockers keep their inline markup.** The spent-budget branches build `UNRESOLVED_CHECKS`
  from `### Blockers` in `get_feedback`, which `CriticFeedback.parse_markdown` had flattened
  (code spans, emphasis and `<…>` lost their markers and gained spaces). An accept-as-is SD
  quoting such a blocker never matched the finding key, so a relayed `implementation.md` finding
  was asked again. `CriticFeedback.blockers` now keeps each item's inline source
  (`MCPModel._extract_list_items_by_header_path(..., keep_inline_markup=True)`, `src/models/base.py`),
  and the empty-blocker sentinel check ignores `*`, `_` and backtick markers so `- **None**` is
  still rejected. Key issues and recommendations are unchanged.
- **Not applied: the prompt-side fix for accepted missing paths.** One review proposed leaving
  Settled Design Decisions in `extract_cited_paths` and telling the architect and critic to skip
  paths an accept SD quotes. Excluding the section server-side does the same thing
  deterministically (judgment call 9), so the prompt change was not made.
- **A failed gate validation fails closed.** Key mode raises when the phase is missing, the
  store fails, or the server predates key mode. Like every other MCP call in Step 9, the gate
  now ends the run with the exact error before any architect or critic is engaged
  (`test_a_failed_gate_validation_ends_the_run_before_any_agent_is_engaged`).

## Out of scope

- **Phase 4's checks:**
  - Grounding, Delegation Bounds, Behaviors & Acceptance and Guardrails
  - the step delegation fields: goal, context pointers, files to create or modify, depends on,
    test IDs, verify, done when
  - `T-n` IDs
  - exemplar-path existence
  - agreement between the two research copies
  - the cold-start check

  Phase 4 extends `check_implementation_structure` and `extract_cited_paths`.
- **A server check that each step names file paths.** The pinned example names only placeholder
  paths (`src/platform/templates/agents/phase_architect.py:58-98`, pinned by
  `test_phase_implementation_plan_gate.py:62`, `:71`). It had none at `a64f0dc`; phase 2 added
  `**Files**: <path to …>` lines. Either way the server has no grammar for a step's files, so it
  cannot tell a missing path from a placeholder or a path-free step. Phase 2's critic check
  ("every `#### Step N:` names the files it touches") and its Test List coverage check stay with
  the critic. Phase 4's "files" field replaces both.
- **RP line and `- Read:` line field format** (tier values, approval marks, `informs`/`Source`).
  The orchestrator writes them deterministically. Only their IDs are checked here.
- **The UX Contract's mechanical rules** (Route Index `auth=`, FLOW pass markers) and Deferred Risk
  Register line format. They stay where they are.
- **Widening the Skeleton Index meta-notation** for identifiers ending in `?` or `!`. That belongs to
  phase 1 / the grammar owner (judgment call 3).
- **Any server-side file-existence check,** in any deployment, and any `project_root` parameter.
- **Content-loss warnings on `store_document`** (the orchestrator path and the disk sync).
- **Repairing the parser traps** (substring matching, `---`, fences). This phase only detects them.
- **Plan and Roadmap validation,** and respec-code and respec-patch readers (frozen).

## Exit criteria

- [x] B1–B18 are pinned, each observed failing for the right reason before its implementation. (S5 audit: evidence files in the session scratchpad `p3-red/`; behaviors green on day one carry temporary-break evidence instead.)
- [x] `uv run pytest` is green (2737 passed, 1 skipped, 2026-11-16; 2807 passed, 1 skipped after the
      review fixes).
- [x] `uv run respec-ai regenerate --force --tui all` completes with no per-TUI failure in a scratch
      project with opencode and codex model tiers configured (README "Per-phase exit criteria").
      (S5: run with a scratch HOME; 21/20/20 agents regenerated, 39 artifact checks pass. Re-run
      after the review fixes with the same result.)
- [x] Both "Already done?" probes print a match, and so does the README phase 3 probe
      (`grep -q … && grep -n …`).
- [x] README "Shared contracts" carries every edit in work item 10.
- [ ] The manual checks below are written as cold-runnable steps P3.1-P3.5 in
      `phase-2-manual-checks.md` ("Phase 3"), so one live session covers phases 2 and 3.
- [ ] Manual, on a scratch project. Use only defects the architect can repair without touching your
      intent:
  - Run a real phase to design review.
  - Hand-edit `phase.md`: add a Skeleton Index line whose path is not in Module Layout, and remove
    the backticks around an existing seam's path.
  - Confirm that neither problem is shown to you, that both are repaired before the design review
    reappears (the missing module is added to Module Layout, and the backticks are restored), and
    that the happy path still has at most three touchpoints.
- [ ] Manual: hand-edit `phase.md` to delete one OD's `Option B`. Restoring it would undo your edit
      (judgment call 5), so expect it to reach you once, as an unresolved check. Accept it as-is,
      send the design back once more, and confirm it is not asked again (B17).
- [ ] Manual: hand-edit `phase.md` to add a bare `---` inside an extra H2 section. The content-loss
      menu shows it to you, and the structural path does not.
- [ ] Manual, on codex and opencode, where grants are prompt-enforced (F14): the architect and the
      critic actually call `validate_document`, and the critic Globs `paths_to_verify`.
- [ ] Manual: read the `validate_document` tool description and a sample of rendered findings
      (`<check> <subject> [<part>] — <detail>`) as the architect would. Each names its subject and
      its fix, and no `detail` names a language. B9 is the machine check.
