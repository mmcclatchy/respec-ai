# Verified findings

Each finding below was confirmed by reading the referenced file, not inferred from documentation or
naming. Line numbers reflect the state of the codebase at the time of the v2 design work; if a
reference no longer matches, re-verify before acting on it.

These are the load-bearing facts underneath [README.md](README.md) and the phase documents.

## The unowned design layer

**F1 — The architect is forbidden from naming files.**
`phase_architect.py:487-489` — *"❌ Specific File Names. Wrong: Create `src/neo4j_client.py`.
Right: Neo4j client module: Connection management, query execution."*
`phase_architect.py:520` justifies this with the quality check *"Does task-planner have freedom to
choose file organization? ✓"*

**F2 — Task has no slot for layout or interfaces.**
`task_planner.py:250-262` enumerates the required sections: Identity, Overview, Implementation,
Quality, Research, Status, Metadata. None hold file layout, class interfaces, or a test list. The
architect deferred to a place that was never built.

**F3 — The coder reads two Phase sections that cannot exist.**
`coder.py:378` — *"Match directory organization from Phase Development Environment section."*
`coder.py:380` — *"Place tests according to Test Organization specifications."*
`src/models/phase.py:14-36` (`HEADER_FIELD_MAPPING`) contains neither section. They are phantoms.

**F4 — Spec-alignment grades against the same phantom.**
`spec_alignment_reviewer.py:182` — *"Award full credit when file placement, module boundaries,
integration points, and sequencing fit the Phase architecture and Development Environment sections."*

**Consequence of F1–F4:** file layout, class shapes, and test placement are invented ad hoc by the
coder on every iteration, and the only corrective signal is post-hoc review.

## The phase workflow never blocks

**F5 — The phase USER_INPUT branch does not stop.**
`phase_command.py:451-458` displays feedback and returns to Step 5. It contains no
`WAIT for {selection_response_source}`, no `store_user_feedback`, and no `{selection_prompt_instructions}`.
Its own protocol at `phase_command.py:407` declares *"user_input → ONLY status that involves the
user. Present feedback and wait for response."*

For contrast, these all block and persist correctly: `task_command.py:438-455`,
`code_command.py:701-765`, `patch_command.py:398-410`.

**F6 — Root cause of F5.**
`src/platform/models/phase.py:15-23` (`PhaseCommandTools.respec_ai_tools`) never included
`RespecAITool.STORE_USER_FEEDBACK`. The branch had no tool to call, so it could not have blocked.

## The markdown parser is fragile

These matter because v2 has a human hand-editing `phase.md` at a gate. Silently discarding a user's
edits would be strictly worse than the opacity being fixed.

**F7 — Headings are matched by substring, not equality.**
`src/models/base.py:47` — `if line.startswith('## ') and h2_header in line:`
`src/models/base.py:64` — `if lines[i].startswith('### ') and h3_header in lines[i]:`
Consequence: any section name that is a substring of another can be mismatched. All v2 section names
must be audited for pairwise containment. Notably `Status` is a substring of `Shape Status`, which is
why the metadata field is named `Shape Gate`.

**F8 — A bare `---` line silently truncates a section.**
`src/models/base.py:63` — the H2 scan terminates on `lines[i].strip() == '---'`. A user typing a
horizontal rule mid-section loses everything after it, with no error.

**F9 — Custom H3s under a mapped H2 are silently dropped.**
`src/models/base.py:277-299` — only *unmapped H2* sections are captured into `additional_sections`.
An H3 the model does not know about, sitting under an H2 it does, vanishes on round trip.

## Frozen fields are already broken

**F10 — `store_phase` and `update_phase` disagree.**
`src/utils/state_manager/in_memory.py:310-331` — `store_phase` carries the explicit comment
*"Does NOT preserve frozen fields - this is a full replacement"* and rebuilds the model with only
`iteration` and `version` carried over.
`src/utils/state_manager/in_memory.py:355-378` and `src/utils/state_manager/postgres.py:503-512` —
`update_phase` preserves `FROZEN_PHASES_FIELDS` (defined in `src/utils/state_manager/base.py`).

The workflow uses `store_document` → `PhaseTools.store` → `store_phase`, i.e. the path that does
**not** preserve. So `frozen=True` on `phase.py:43-46` protects nothing on the live path.

**F11 — The storage comment claiming preservation is false.**
`phase_command.py:811` states storage *"ensures immutable initial fields are preserved."* Per F10 it
does not.

**F12 — The roadmap seeds the frozen four, which is why freezing exists.**
`create_phase.py:10-13` sets `objectives`, `scope`, `dependencies`, `deliverables` from the roadmap.
The freeze exists to protect roadmap intent from agent drift — a real purpose, confirmed by the
project owner as a response to observed drift. This is why v2 repairs the mechanism rather than
deleting it.

## Storage and configuration hazards

**F13 — The postgres phases UPSERT is positional.**
`src/utils/state_manager/postgres.py:453-485` uses `$1..$19` with `additional_sections = $19`.
Adding or removing a column shifts every subsequent index. An off-by-one here is **silent data
corruption**, not a crash. Rewrite the column list and renumber in a single pass; do not patch
indices individually.

Note: `phases.task_breakdown` (the column) and `DocumentType.TASK_BREAKDOWN` (the enum) are unrelated
things that share a name. Do not conflate them.

**F14 — `LoopConfig` forbids extra environment keys.**
`src/utils/setting_configs.py:14-30` — `model_config = SettingsConfigDict(extra='forbid', env_prefix='LOOP_')`.
Deleting the `task_threshold` / `task_improvement_threshold` / `task_checkpoint_frequency` fields
means any environment with `LOOP_TASK_THRESHOLD` exported raises a `ValidationError` at **import
time**, bricking both the MCP server and the CLI — not just the task code path. Ship one release with
`extra='ignore'`, or document the break prominently.

**F15 — Loop thresholds resolve by `getattr`, so a missing field fails late.**
`src/utils/enums.py:13-23` — `return getattr(loop_config, f'{self.value}_threshold')`. Adding a new
`LoopType` without adding all three corresponding `LoopConfig` fields produces an `AttributeError` at
*decision* time, deep inside a live workflow, rather than at import. This is why v2 reuses
`LoopType.PHASE` for both acts instead of adding `LoopType.SHAPE`.

**F16 — Blocker gating applies only to explicitly listed critics.**
`src/utils/loop_state.py:49-52` — `_MARKER_BLOCKER_GATE_CRITICS` = {`REVIEW_CONSOLIDATOR`,
`CODING_STANDARDS_REVIEWER`}.
`src/utils/loop_state.py:53-59` — `_DOCUMENT_BLOCKER_STAGNATION_CRITICS` = the five document critics,
including `PHASE_CRITIC`.
A new critic in neither set silently gets no marker-blocker gate and no blocker-stagnation
escalation, with nothing in the type system to signal it. This is why v2 reuses
`CriticAgent.PHASE_CRITIC` with a `phase_mode` flag rather than adding a shape critic.

**F17 — `_COMMAND_CATEGORY_BY_NAME` is indexed directly.**
`src/platform/template_generator.py:79-89` defines it; `:142` indexes it without a guard. Omitting an
entry for a registered command is a `KeyError`, not a fallback.

## Platform and path

**F18 — Codex has no AskUserQuestion.**
`src/platform/tui_adapters/codex.py:71` — `BuiltInToolCapability.ASK_USER_QUESTION: None`.
`src/platform/tui_adapters/base.py:65-74` supplies the fallback: templates must use
`{selection_prompt_instructions}` and `WAIT for {selection_response_source}`, never a literal tool
name. Codex renders these as a numbered chat list.

**F19 — Phase file and directory share a stem, making globs ambiguous.**
Current layout is `phases/{PHASE_NAME}.md` alongside `phases/{PHASE_NAME}/tasks/`.
`src/platform/adapters/markdown.py:10` globs `phases/{PHASE_NAME_PARTIAL}*.md` and `:123` globs
`phases/*.md`, against a namespace where the phase name denotes both a file and a directory.

**F20 — The phase command calls `Read()` without holding the capability.**
`phase_command.py:551` reads `.best-practices/*.md` paths, but
`src/platform/template_helpers.py:150-168` (`create_phase_command_tools`) never adds
`BuiltInToolCapability.READ`. Pre-existing bug, unrelated to v2 but fixed alongside it.

**F21 — The patch byte-integrity gate is name-based, not content-based.**
`patch_command.py:1086-1125` strips `## Evolution Log` and requires the remainder to match
byte-for-byte. Because the rule keys on section names rather than content shape, adding new sections
to Phase does not break it — the protected enumeration at `:1101-1103` simply needs extending.

## Useful primitive

**F22 — `Phase.version` increments on every store.**
`src/models/phase.py:71` defines it; `src/utils/state_manager/in_memory.py:320-326` increments it on
each `store_phase`. This gives the v2 joint gate free tracking of *"has the design changed since the
user approved it"* with no new state.
