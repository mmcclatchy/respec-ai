from src.platform.models import CodeCommandTools
from src.utils.language_extensions import FRONTEND_EXTENSIONS


def generate_code_command_template(tools: CodeCommandTools) -> str:
    selection_prompt_instructions = tools.tui_adapter.selection_prompt_instruction
    selection_response_source = tools.tui_adapter.selection_response_source
    # Data-driven from the extension map (F14) rather than a second hardcoded list that
    # drifts from it -- an .astro or .mdx project now activates frontend mode too.
    frontend_extensions_glob = ', '.join(f'*{ext}' for ext in sorted(FRONTEND_EXTENSIONS))
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase request]
description: Transform Phases into production-ready code through TDD-driven implementation
---

# respec-code Command: Implementation Orchestration

## Overview
Orchestrate the complete implementation workflow, transforming Phases into production-ready code through TDD-driven code development with comprehensive quality validation.

{tools.mcp_tools_reference}

{tools.tui_adapter.subagent_invocation_guardrail}

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed above.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: result = tool_name(param="value")
  ❌ WRONG: <tool_name><param>value</param>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

═══════════════════════════════════════════════
ORCHESTRATOR BOUNDARY
═══════════════════════════════════════════════
This command is an orchestrator, not an implementation agent.

Allowed command responsibilities:
- Parse and clarify user inputs
- Resolve Phase, implementation plan, execution mode, and active reviewers
- CALL MCP tools
- Invoke specialized agents
- Consolidate review results
- Run pre-commit, commit, and workflow documentation orchestration
- Update Phase implementation documentation

Forbidden command responsibilities:
- Do NOT directly edit source code.
- Do NOT directly edit tests.
- Do NOT manually implement the requested code.
- Do NOT substitute command-local implementation for a missing or failed coder agent.

Implementation responsibility:
- ALL source-code and test implementation MUST be delegated to `respec-coder`.
- If `respec-coder` cannot be invoked, fail closed with diagnostics.
- If `respec-coder` fails, follow the coder failure branch; do not continue by implementing code in this command.
═══════════════════════════════════════════════

## Workflow Steps

### 1. Parse User Inputs and Locate Phase File

Parse user inputs and locate the target phase without guessing at free-form boundaries:

#### Step 1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the project name]
RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]
```

#### Step 1.1.1: Initialize workflow variables

```text
PHASE_NAME_PARTIAL = [empty until RAW_PHASE_REQUEST is clarified]
OPTIONAL_CONTEXT = [empty until RAW_PHASE_REQUEST is clarified]
GUIDANCE_DOCUMENT_PATHS = []
```

Fail closed on ambiguity:
- Treat RAW_PHASE_REQUEST as the only user-authored source of truth after PLAN_NAME.
- Do NOT assume RAW_PHASE_REQUEST has a clean boundary between the phase reference
  and additional implementation guidance.
- Ask the user a clarifying question or present options whenever multiple reasonable
  interpretations would change the selected phase, scope, implementation direction,
  validation criteria, or what to pass downstream as guidance.
- Do NOT begin phase lookup until the phase reference is sufficiently clear.

Once RAW_PHASE_REQUEST is sufficiently clear:
- PHASE_NAME_PARTIAL = [clarified phase selector derived from RAW_PHASE_REQUEST]
- OPTIONAL_CONTEXT = [remaining clarified implementation guidance, otherwise empty string]

Guidance document path handling:
- If RAW_PHASE_REQUEST or OPTIONAL_CONTEXT contains readable project-local document paths
  intended to guide implementation (for example `.md`, `.txt`, `.rst`, or `.adoc` files),
  add each path to GUIDANCE_DOCUMENT_PATHS.
- Do NOT use a guidance document path as PHASE_NAME_PARTIAL unless it is itself a valid
  Phase file under the configured phase location.
- Validate each guidance document path before invoking subagents:
  - Relative paths are resolved from the target project working directory.
  - Paths MUST stay inside the target project working directory.
  - Paths MUST exist and be readable.
  - Invalid or outside-project paths are preserved in OPTIONAL_CONTEXT as reported user intent,
    but are NOT passed as readable guidance paths; ask for clarification if the missing path
    changes scope or implementation direction.
- Keep GUIDANCE_DOCUMENT_PATHS separate from implementation files to edit. These are read-only
  context documents that inform agent work.

If OPTIONAL_CONTEXT is present after clarification, preserve it for the full
code-implementation loop and pass it through to the coder, all reviewers, and
the deterministic MCP consolidation step.

#### Step 1.2: Search file system for matching phase files

```text
{tools.phase_discovery_instructions}
```

#### Step 1.3: Handle multiple matches

```text
IF count(SPEC_FILE_MATCHES) == 0:
  ERROR: "No Phase files found matching '{{PHASE_NAME_PARTIAL}}' in project {{PLAN_NAME}}"
  SUGGEST: "Verify the phase name or check {tools.phase_location_hint}"
  EXIT: Workflow terminated

ELIF count(SPEC_FILE_MATCHES) == 1:
  PHASE_FILE_PATH = PHASE_FILE_MATCHES[0]

ELSE:
  (Multiple matches - use interactive selection)
  {selection_prompt_instructions}
    Question: "Multiple phase files match '{{PHASE_NAME_PARTIAL}}'. Which one do you want to use?"
    Header: "Select Phase"
    multiSelect: false
    Options: [
      {{
        "label": "{{PHASE_FILE_MATCHES[0]}}",
        "description": "Use: {{PHASE_FILE_MATCHES[0]}}"
      }},
      {{
        "label": "{{PHASE_FILE_MATCHES[1]}}",
        "description": "Use: {{PHASE_FILE_MATCHES[1]}}"
      }},
      ... for all matches
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 1.3. Set PHASE_FILE_PATH. Continue to Step 1.4 immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  PHASE_FILE_PATH = [selected file path from {selection_response_source}]
```

#### Step 1.4: Extract canonical name from file path

```text
PHASE_NAME = [basename of the parent directory of PHASE_FILE_PATH]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-2a")
- PHASE_NAME is the canonical name extracted from file path
- PLAN_NAME is used for all MCP storage operations
- All subsequent operations use PHASE_NAME (canonical)

### 2. Load and Store Existing Spec

Load phase from file system, store in MCP:

```text
{tools.sync_phase_instructions}
```

**Important**:
- PHASE_FILE_PATH is the full path from Step 1
- PHASE_NAME is the canonical name extracted from file path
- Phase is now in MCP storage for build workflow

**Note**: Build plans are not stored in external platforms - they only exist in MCP during the build workflow.

**Note on Step Numbering**: Step 3 was intentionally removed when research logic was moved to the phase workflow. Step numbering is preserved (1, 2, 4, 5...) for workflow compatibility.

### 4. Phase Validation
Coder agent will validate Phase exists when retrieving it:

```text
# Phase validation delegated to coder agent
# Coder retrieves Phase using loop_id and handles missing Phase error
# This follows the token optimization pattern - agents retrieve their own data
```

### 5. Resolve Phase and Read the Implementation Plan

One Phase, no ambiguity — there is no Task selection menu. Link a phase-type loop to
the Phase document, then read implementation.md by path.

```text
PHASE_LOOP_ID = {tools.initialize_phase_loop}
{tools.link_phase_loop}
PHASE_MARKDOWN = {tools.get_phase_document}

IF PHASE_MARKDOWN retrieval fails:
  ERROR: "Phase document could not be retrieved for {{PLAN_NAME}}/{{PHASE_NAME}}"
  DIAGNOSTIC: [surface the exact MCP/tool error]
  FAIL-CLOSED:
  - Do NOT initialize coding loop
  - Do NOT invoke coder
  EXIT: Workflow terminated

SHAPE_GATE = [extract "### Shape Gate" value from PHASE_MARKDOWN]

IF SHAPE_GATE not in ["shape-settled", "shape-amended"]:
  ERROR: "Phase design was never settled by the human gate"
  DIAGNOSTIC: "### Shape Gate is '{{SHAPE_GATE}}', not 'shape-settled' or 'shape-amended'"
  SUGGEST: "Run the Phase workflow (respec-phase) to settle the design before coding"
  FAIL-CLOSED:
  - Do NOT initialize coding loop
  - Do NOT invoke coder
  EXIT: Workflow terminated

PHASE_FILE_PATH = "{tools.phase_resource_pattern}"
PHASE_DIR = dirname(PHASE_FILE_PATH)
IMPLEMENTATION_PLAN_PATH = f"{{PHASE_DIR}}/implementation.md"
IMPLEMENTATION_PLAN_MARKDOWN = Read(IMPLEMENTATION_PLAN_PATH)

IF Read fails:
  ERROR: "implementation.md could not be read at {{IMPLEMENTATION_PLAN_PATH}}"
  DIAGNOSTIC: [surface the exact filesystem error]
  SUGGEST: "Run the Phase workflow (respec-phase) to produce implementation.md before coding"
  FAIL-CLOSED:
  - Do NOT initialize coding loop
  - Do NOT invoke coder
  EXIT: Workflow terminated

Display: "✓ Phase and implementation plan resolved for {{PHASE_NAME}}"
```

### 6. Check for a Shape Amendment Request

Use Phase already retrieved in Step 5:

```text
# REUSE PHASE_MARKDOWN from Step 5 (do not re-retrieve)

IF PHASE_MARKDOWN's "### Design Shape - Additional Sections" contains a
"#### Shape Amendment Request" subsection:
  AMENDMENT_SECTION = [Extract subsection content]

  IF AMENDMENT_SECTION is not empty (has content beyond just header):
    Display to user:
    "⚠️ A prior iteration flagged a potential design shape change.

    Review the Shape Amendment Request in the Phase document.

    Choose action:
    1. Approve → Re-run phase workflow to update the design shape
    2. Reject → Continue with current Phase as-is

    Coding workflow paused until Phase updated.

    To approve:
    {tools.phase_command_invocation}
    To reject:
    {tools.code_command_invocation}

    EXIT: Workflow suspended pending user decision

IMMEDIATELY execute Step 6.5 (Mode Extraction) and Step 6.7 (Delivery Intent Resolution)
```

### 6.5 Extract Step Modes from the Implementation Plan

Parse implementation.md and the Phase's Skeleton Index to determine which specialist
reviewers to activate. File paths are a stronger reviewer signal than prose keywords,
so scan both:

```text
# REUSE IMPLEMENTATION_PLAN_MARKDOWN and PHASE_MARKDOWN from Step 5 (do not re-retrieve)

STEP_MODES = set()

For each "#### Step N:" section in IMPLEMENTATION_PLAN_MARKDOWN's "## Build Order > ### Steps":
  Scan Step content for mode indicators:
  IF contains frontend keywords (UI, component, template, CSS, accessibility, HTMX, hx-, React, Vue, Svelte, Alpine.js, aria-, semantic HTML, form validation, responsive):
    STEP_MODES.add("frontend")
  IF contains API keywords (endpoint, REST, route, request, response, authentication, middleware):
    STEP_MODES.add("api")
  IF contains database keywords (schema, migration, model, query, index, SQL, ORM):
    STEP_MODES.add("database")
  IF contains infrastructure keywords (Docker, CI/CD, deployment, container, pipeline, environment):
    STEP_MODES.add("infrastructure")

For each `path :: signature` line in PHASE_MARKDOWN's "### Skeleton Index":
  Scan the path for mode indicators:
  IF path matches frontend locations (templates/, static/, components/, {frontend_extensions_glob}):
    STEP_MODES.add("frontend")
  IF path matches API locations (routes/, api/, endpoints/, controllers/):
    STEP_MODES.add("api")
  IF path matches database locations (migrations/, models/, schema/, *.sql):
    STEP_MODES.add("database")
  IF path matches infrastructure locations (Dockerfile, docker-compose*, .github/workflows/, deploy/):
    STEP_MODES.add("infrastructure")

Display: "✓ Detected step modes: {{STEP_MODES}}"
```

### 6.6 Resolve Active Reviewers

Determine which review agents to invoke based on detected modes:

```text
ACTIVE_REVIEWERS = ["automated-quality-checker", "spec-alignment-reviewer", "code-quality-reviewer"]

IF "frontend" in STEP_MODES:
  ACTIVE_REVIEWERS.append("frontend-reviewer")
IF "api" in STEP_MODES:
  ACTIVE_REVIEWERS.append("backend-api-reviewer")
IF "database" in STEP_MODES:
  ACTIVE_REVIEWERS.append("database-reviewer")
IF "infrastructure" in STEP_MODES:
  ACTIVE_REVIEWERS.append("infrastructure-reviewer")

IF PHASE_MARKDOWN's "### Skeleton Index" is non-empty:
  ACTIVE_REVIEWERS.append("design-conformance-reviewer")

Check for canonical coding standards config files:
STANDARDS_TOML_FILES = Glob(.respec-ai/config/standards/*.toml)
LANGUAGE_TOML_FILES = STANDARDS_TOML_FILES excluding universal.toml
IF LANGUAGE_TOML_FILES is not empty:
  ACTIVE_REVIEWERS.append("coding-standards-reviewer")

Read config files for coder agent:
STACK_CONFIG = Read(.respec-ai/config/stack.toml) if file exists, else ""
LANGUAGE_CONFIGS = For each file in LANGUAGE_TOML_FILES:
  Read(file) — concatenated content
GUIDE_FILES = Glob(.respec-ai/config/standards/guides/*.md)
STANDARDS_GUIDE = For each file in GUIDE_FILES:
  If filename stem matches a LANGUAGE_TOML_FILES stem: Read(file) — concatenated content
If no guide files match: STANDARDS_GUIDE = ""

WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:
  ## Workflow Guidance
  ### Guidance Summary
  [OPTIONAL_CONTEXT if present, otherwise "None"]
  ### Guidance Document Paths
  - [each validated path from GUIDANCE_DOCUMENT_PATHS]
  - None
  ### Constraints
  - [preserved constraint from OPTIONAL_CONTEXT]
  - None
  ### Resume Context
  - [resume detail from OPTIONAL_CONTEXT]
  - None
  ### Settled Decisions
  - [clarified decision from OPTIONAL_CONTEXT]
  - None

PROJECT_CONFIG_CONTEXT_MARKDOWN = compose markdown:
  ## Project Config Context
  ### Stack Config TOML
  ```toml
  [STACK_CONFIG if present, otherwise "None"]
  ```
  ### Language Config TOMLs
  ```toml
  [LANGUAGE_CONFIGS if present, otherwise "None"]
  ```
  ### Standards Guide Markdown
  ```markdown
  [STANDARDS_GUIDE if present, otherwise "None"]
  ```

# Loop IDs in this command:
#   PHASE_LOOP_ID     — loop linked to the Phase document (Step 5)
#   CODING_LOOP_ID    — Phase 1 functional loop (AQC + spec-alignment + domains)
#   STANDARDS_LOOP_ID — Phase 2 standards loop (coding-standards-reviewer only)
# Coder receives the loop ID matching its current phase.
# Each agent retrieves its own feedback using the loop_id it was given.

PHASE1_REVIEWERS = ACTIVE_REVIEWERS excluding "coding-standards-reviewer"
(coding-standards-reviewer runs in Phase 2 only)

Display: "✓ Active reviewers: {{ACTIVE_REVIEWERS}}"
Display: "✓ Phase 1 reviewers: {{PHASE1_REVIEWERS}}"
```

### 6.7 Resolve Delivery Intent Policy

Resolve execution mode deterministically before coding/review:

```text
# Required documents for policy resolution
PHASE_MARKDOWN = {tools.get_phase_document}
PLAN_MARKDOWN = mcp__respec-ai__get_document(doc_type="plan", key=PLAN_NAME, loop_id=None)
# REUSE IMPLEMENTATION_PLAN_MARKDOWN from Step 5 (do not re-retrieve)

# Parse policy blocks (if present)
PHASE_POLICY = extract from IMPLEMENTATION_PLAN_MARKDOWN:
  "## Policy > ### Execution Intent Policy"
PLAN_DEFAULT = extract from PLAN_MARKDOWN:
  "## Quality Assurance > ### Delivery Intent Policy > Default Mode"
PLAN_TIE_BREAK = extract from PLAN_MARKDOWN:
  "## Quality Assurance > ### Delivery Intent Policy > Tie-Break Policy"

# Deterministic precedence (two levels — phase-policy vs plan-default; the old
# per-phase delivery-intent override variable was removed when implementation.md's
# Execution Intent Policy became the single home for this)
IF PHASE_POLICY has valid Mode in {{MVP,hardening}}:
  RESOLVED_MODE = PHASE_POLICY.mode
  RESOLVED_MODE_SOURCE = "phase-policy"
ELIF PLAN_DEFAULT has valid Mode in {{MVP,hardening}}:
  RESOLVED_MODE = PLAN_DEFAULT
  RESOLVED_MODE_SOURCE = "plan-default"
ELSE:
  RESOLVED_MODE = "MVP"
  RESOLVED_MODE_SOURCE = "default-MVP"

RESOLVED_TIE_BREAK = first non-empty of:
  PHASE_POLICY.tie_break, PLAN_TIE_BREAK,
  "Prioritize core functional/spec delivery and defer non-P0 hardening risks."

AMBIGUOUS_MODE = conflicting explicit values across phase/plan sources

IF AMBIGUOUS_MODE:
  {selection_prompt_instructions}
    Header: "Resolve Mode"
    Question: "Delivery intent sources conflict. Select the mode for this coding loop."
    multiSelect: false
    Options:
      - MVP
      - hardening

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 6.7. Set RESOLVED_MODE. Continue to the resolved-mode display immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  RESOLVED_MODE = [user choice]
  RESOLVED_MODE_SOURCE = "user-selected-conflict-resolution"
```

Display:
- "✓ Resolved execution mode: {{RESOLVED_MODE}} (source: {{RESOLVED_MODE_SOURCE}})"
- "✓ Tie-break policy: {{RESOLVED_TIE_BREAK}}"

### 7. Coding Loop Initialization and Refinement
Set up and execute MCP-managed code quality refinement:

#### Step 7.1: Initialize Coding Loop
```text
CODING_LOOP_ID = {tools.initialize_coding_loop}
```

#### Step 7.2: CRITICAL - Dual Loop ID Management

You now have TWO active loop IDs - DO NOT confuse them:

**phase_loop_id = {{PHASE_LOOP_ID}}**
- Purpose: Identifies the loop linked to the Phase document (Step 5)
- Used by: coder and reviewers, to verify against Phase and implementation.md
- Storage: Phase document linked to this loop

**coding_loop_id = {{CODING_LOOP_ID}}**
- Purpose: Store/retrieve code feedback
- Used by: coder (feedback retrieval), reviewers (structured result storage), MCP consolidation
- Storage: CriticFeedback for code quality

Pass BOTH IDs to coding agents. Never swap them.

#### Step 7.2.1: Persist Mode Snapshot to Loop Feedback

```text
MODE_SNAPSHOT_MARKDOWN = "## Execution Intent Snapshot\\n"
  + "- Mode: {{RESOLVED_MODE}}\\n"
  + "- Source: {{RESOLVED_MODE_SOURCE}}\\n"
  + "- Tie-Break Policy: {{RESOLVED_TIE_BREAK}}\\n"
  + "- Deferred Risk Register Source: implementation.md Policy > Deferred Risk Register"

LOOP_ID = CODING_LOOP_ID
USER_FEEDBACK_MARKDOWN = MODE_SNAPSHOT_MARKDOWN
{tools.store_user_feedback}
```

#### Step 7.4: Phase 1 Iteration Loop (Coder → Reviews → Decision → Commit)

```text
RUN_BASE_REF = RUN_BASE_REF if defined else [result of: git rev-parse HEAD]
PHASE1_SIGNED_OFF_REVIEWERS = PHASE1_SIGNED_OFF_REVIEWERS if defined else []

Loop:
  REVIEW_ITERATION = REVIEW_ITERATION if defined else 1

  # A) Coder pass
  {tools.invoke_coder}
  IF coder reports failure:
    ERROR: "Coder failed"
    DIAGNOSTIC: [surface the exact coder error/output]
    FAIL-CLOSED:
    - Do NOT invoke reviewers
    - Do NOT call consolidate_review_cycle
    - Do NOT call decide_coding_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  # B) Phase 1 review team orchestration
  PHASE1_REVIEWERS_TO_INVOKE = []
  PHASE1_INVALIDATED_REVIEWERS = []

  Set PHASE1_INVALIDATED_REVIEWERS by applying these rules to each reviewer in PHASE1_SIGNED_OFF_REVIEWERS:
  - Compare the coder run summary, changed files, implementation-plan/phase context changes, and prior consolidated feedback.
  - Add a signed-off reviewer when new or changed work touches that reviewer's responsibility.
  - Add all Phase 1 reviewers when implementation.md, the Phase document, execution mode, public behavior,
    API contracts, persistence behavior, integration boundaries, dependency wiring, migrations, build tooling,
    test harness, or security-sensitive behavior changed since that reviewer signed off.
  - Rerun on uncertainty by adding the uncertain reviewer.

  For each REVIEWER in PHASE1_REVIEWERS:
    IF REVIEWER not in PHASE1_SIGNED_OFF_REVIEWERS:
      add REVIEWER to PHASE1_REVIEWERS_TO_INVOKE
    ELSE IF REVIEWER is in PHASE1_INVALIDATED_REVIEWERS:
      add REVIEWER to PHASE1_REVIEWERS_TO_INVOKE

  IF PHASE1_REVIEWERS_TO_INVOKE is empty:
    Display: "✓ Reusing prior Phase 1 reviewer sign-offs for this iteration"
  ELSE:
    Launch only PHASE1_REVIEWERS_TO_INVOKE in parallel.{tools.phase1_review_parallel_policy}

  Core reviewers:
  IF "automated-quality-checker" in PHASE1_REVIEWERS_TO_INVOKE:
    {tools.invoke_quality_checker}
  IF "spec-alignment-reviewer" in PHASE1_REVIEWERS_TO_INVOKE:
    {tools.invoke_spec_alignment}
  IF "code-quality-reviewer" in PHASE1_REVIEWERS_TO_INVOKE:
    {tools.invoke_code_quality}

  Optional specialists:
  For each REVIEWER in PHASE1_REVIEWERS_TO_INVOKE where REVIEWER is not core:
    {tools.invoke_dynamic_reviewer_pattern}

  REVIEW_FAILURE_REPORTS = collect invoked reviewers that report failure, return no run summary,
  report run_status=incomplete, fail to confirm stored_result=yes, or fail to confirm stored reviewer result.

  IF REVIEW_FAILURE_REPORTS is not empty:
    FAILED_REVIEWERS = [reviewer names from REVIEW_FAILURE_REPORTS]
    Display: "Phase 1 reviewer failure detected. Restarting failed reviewer(s) once: {{FAILED_REVIEWERS}}"

    For each FAILED_REVIEWER in FAILED_REVIEWERS:
      Close the failed reviewer subagent handle if the runtime exposes one.
      Restart only FAILED_REVIEWER with the same invocation inputs and same REVIEW_ITERATION.
      Use this deterministic invocation mapping:
      - automated-quality-checker: rerun the automated-quality-checker core reviewer block above.
      - spec-alignment-reviewer: rerun the spec-alignment-reviewer core reviewer block above.
      - code-quality-reviewer: rerun the code-quality-reviewer core reviewer block above.
      - any optional specialist: set REVIEWER = FAILED_REVIEWER, then run the optional specialist dynamic invocation pattern above.
      Do NOT restart unaffected reviewers in this recovery step.

    REVIEW_RESTART_FAILURE_REPORTS = collect restarted reviewers that report failure, return no run summary,
    report run_status=incomplete, fail to confirm stored_result=yes, or fail to confirm stored reviewer result.

    IF REVIEW_RESTART_FAILURE_REPORTS is not empty:
      Display: "Reviewer restart did not clear all failures. Rerunning full Phase 1 review pass once."
      Rerun every reviewer in PHASE1_REVIEWERS_TO_INVOKE with the same invocation inputs and same REVIEW_ITERATION.
      Use the deterministic invocation mapping from the failed-reviewer restart step for each reviewer.
      The rerun intentionally reuses REVIEW_ITERATION because reviewer-result storage upserts by loop, iteration, and reviewer.

      FULL_REVIEW_RERUN_FAILURE_REPORTS = collect rerun reviewers that report failure, return no run summary,
      report run_status=incomplete, fail to confirm stored_result=yes, or fail to confirm stored reviewer result.

      IF FULL_REVIEW_RERUN_FAILURE_REPORTS is not empty:
        ERROR: "Phase 1 review team failed after bounded recovery"
        DIAGNOSTIC: compose detailed report containing:
        - initial REVIEW_FAILURE_REPORTS
        - restart REVIEW_RESTART_FAILURE_REPORTS
        - full rerun FULL_REVIEW_RERUN_FAILURE_REPORTS
        - reviewer names, review iteration, failed step/stage, tool/command in use,
          prompt/invocation inputs, exact error output, retry/fallback response,
          storage status, and recommended orchestrator action from each reviewer
        FAIL-CLOSED:
        - Do NOT call consolidate_review_cycle
        - Do NOT call decide_coding_action
        - Do NOT invoke respec-commit
        EXIT: Workflow terminated

  # Consolidate deterministic reviewer results into CriticFeedback
  LOOP_ID = CODING_LOOP_ID
  ACTIVE_REVIEWERS = PHASE1_REVIEWERS
  CONSOLIDATION_RESPONSE = {tools.consolidate_review_cycle}
  IF consolidate_review_cycle reports failure:
    ERROR: "Phase 1 review consolidation failed"
    DIAGNOSTIC: [surface the exact MCP/tool error]
    FAIL-CLOSED:
    - Do NOT call decide_coding_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  IF CONSOLIDATION_RESPONSE.iteration != REVIEW_ITERATION:
    ERROR: "Phase 1 review consolidation iteration mismatch"
    DIAGNOSTIC: [surface CONSOLIDATION_RESPONSE and REVIEW_ITERATION]
    FAIL-CLOSED:
    - Do NOT call decide_coding_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  PHASE1_FEEDBACK = {tools.get_feedback}
  IF PHASE1_FEEDBACK is empty OR retrieval fails:
    ERROR: "Phase 1 consolidated feedback missing"
    DIAGNOSTIC: [surface the exact MCP/tool error]
    FAIL-CLOSED:
    - Do NOT call decide_coding_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  Update PHASE1_SIGNED_OFF_REVIEWERS from the consolidated reviewer sections:
  - Add a reviewer when its latest result has full score, no blockers, and no P0/P1 findings.
  - Remove a reviewer when its latest result has any blocker, any P0/P1 finding, or less than full score.
  - Keep a reused reviewer signed off only when it was not invalidated this iteration.

  # C) MCP coding decision
  CODING_DECISION_RESPONSE = {tools.decide_coding_action}
  CODING_DECISION = CODING_DECISION_RESPONSE.status
  CODING_SCORE = CODING_DECISION_RESPONSE.current_score
  CODING_ITERATION = CODING_DECISION_RESPONSE.iteration
  Decision options: "completed", "refine", "user_input"

  # D) Phase 1 commit orchestration (every pass)
  # Loop commits are progress checkpoints only.
  # Completion commit is owned by Step 8.5 finalization gate.
  COMMIT_KIND = "phase1-checkpoint"
  COMMIT_WORKFLOW_KIND = "code"
  ALLOW_EMPTY = true
  {tools.commit_command_invocation}

  # E) Decision handling after commit
  IF CODING_DECISION == "refine":
    REVIEW_ITERATION = CODING_ITERATION + 1
    continue loop

  IF CODING_DECISION == "completed":
    exit loop to Step 8

  IF CODING_DECISION == "user_input":
    exit loop to Step 8
```

### 8. Coding Decision Handling

═══════════════════════════════════════════════
MANDATORY DECISION PROTOCOL
═══════════════════════════════════════════════
The MCP decision is FINAL. Execute the matching branch IMMEDIATELY.

"refine"     → Execute refinement. Do NOT ask, confirm, or present options to the user.
"user_input" → ONLY status that involves the user. Present feedback and wait for response.
"completed"  → Proceed to next step. Do NOT ask for confirmation.

VIOLATION: Asking the user whether to continue refining when status is "refine"
           is a workflow violation. The decision has already been made by the MCP server.
═══════════════════════════════════════════════

═══════════════════════════════════════════════
MANDATORY CODING LOOP LIMIT
═══════════════════════════════════════════════
Maximum coding loop iterations: 8

IF CODING_ITERATION >= 8 AND CODING_DECISION == "refine":
  Force "user_input" path — present feedback and wait for user guidance
  Display: "⚠ Coding loop reached iteration limit (8)"
═══════════════════════════════════════════════

```text
IF CODING_DECISION == "refine":
  Display: "🔵 [Phase 1 · Iteration {{CODING_ITERATION}}] ⟳ Rubric Score: {{CODING_SCORE}}/100 — decision={{CODING_DECISION}}; refining"
  Return to Step 7.4 (next loop pass runs coder → reviews → decision → commit).

ELIF CODING_DECISION == "completed":
  Display: "🔵 [Phase 1 · Complete] ✅ Rubric Score: {{CODING_SCORE}}/100 — ready for next phase (threshold met, no active blockers)"
  IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
    → IMMEDIATELY execute Step 7.5 (Standards Finalization Phase)
  ELSE:
    FINALIZATION_DECISION_SOURCE = "phase1-complete"
    → IMMEDIATELY execute Step 8.5 (Completion Gate)
  DO NOT ask user, DO NOT offer alternatives, DO NOT pause

ELIF CODING_DECISION == "user_input":
  LATEST_FEEDBACK = {tools.get_feedback}
  P0_ACTIVE = LATEST_FEEDBACK contains any of:
    "[Severity:P0]", "severity=P0", "**[P0]**", "[BLOCKING]"

  Display LATEST_FEEDBACK to user with:
  - Current rubric score and iteration
  - Key issues requiring attention
  - Recommended improvements

  IF P0_ACTIVE:
    {selection_prompt_instructions}
      1. Continue refine in current mode
      2. Switch mode and continue refine
  ELSE:
    {selection_prompt_instructions}
      1. Continue refine in current mode
      2. Switch mode and continue refine
      3. Finalize now with deferred-risk summary

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 8. Branch on the selected option. Continue with the matching action immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF user selects option 1:
    USER_FEEDBACK_MARKDOWN = "User selected continue refine in mode={{RESOLVED_MODE}}"
    LOOP_ID = CODING_LOOP_ID
    {tools.store_user_feedback}
    REVIEW_ITERATION = CODING_ITERATION + 1
    Return to Step 7.4

  IF user selects option 2:
    {selection_prompt_instructions}
      Header: "Switch Mode"
      Question: "Select new execution mode for this loop."
      Options: MVP, hardening
    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 8. Set RESOLVED_MODE. Continue with the loop-feedback update immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.
    RESOLVED_MODE = [user selection]
    RESOLVED_MODE_SOURCE = "user-switched-during-user_input"
    USER_FEEDBACK_MARKDOWN = "Execution Intent Snapshot updated: mode={{RESOLVED_MODE}} (switched by user)"
    LOOP_ID = CODING_LOOP_ID
    {tools.store_user_feedback}
    REVIEW_ITERATION = CODING_ITERATION + 1
    Return to Step 7.4

  IF user selects option 3:
    IF P0_ACTIVE:
      Display: "Cannot finalize while active P0 issues exist."
      Return to user_input options.
    ELSE:
      USER_FEEDBACK_MARKDOWN = "User finalized with deferred-risk summary in mode={{RESOLVED_MODE}}"
      LOOP_ID = CODING_LOOP_ID
      {tools.store_user_feedback}
      FINALIZATION_DECISION_SOURCE = "phase1-user-finalized"
      Proceed directly to Step 8.5 (Completion Gate)
```

### 7.5: Standards Finalization Phase

═══════════════════════════════════════════════
MANDATORY PHASE 2 ACTIVATION GATE
═══════════════════════════════════════════════
Run ONLY IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS
(standards TOML files detected in Step 6.6).

IF no standards TOML files were found in .respec-ai/config/standards/:
  Skip Phase 2 entirely. Proceed directly to Step 8.5.
  Display: "ℹ️ No coding standards configured — skipping Phase 2"

Phase 2 has ZERO built-in rules. Without standards TOML files, there is
nothing to assess. Do NOT apply general coding standards.
═══════════════════════════════════════════════

#### Step 7.5.1: Initialize Standards Loop

```text
STANDARDS_LOOP_ID = {tools.initialize_standards_loop}
STANDARDS_REVIEW_ITERATION = 1

PHASE1_SCORE = [final Overall Score from CODING_LOOP_ID CriticFeedback]
Display:
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  PHASE 1 COMPLETE  ·  Functional Rubric Score: {{PHASE1_SCORE}}/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟣  PHASE 2 STARTING: Coding Standards
    Focus: naming · imports · type hints · docstrings
    Command orchestration owns commit lifecycle.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

#### Step 7.5.2: Standards Review Cycle

```text
Loop:
  REVIEW_ITERATION = STANDARDS_REVIEW_ITERATION

  # A) Build deterministic changed-file scope for the standards reviewer
  CHANGED_FILES_FROM_BASE = [result of: git diff --name-only RUN_BASE_REF..HEAD --diff-filter=AM]
  CHANGED_FILES_UNSTAGED = [result of: git diff --name-only --diff-filter=AM]
  CHANGED_FILES_STAGED = [result of: git diff --cached --name-only --diff-filter=AM]
  CHANGED_FILES_SCOPE = de-duplicated union of:
    1. CHANGED_FILES_FROM_BASE
    2. CHANGED_FILES_UNSTAGED
    3. CHANGED_FILES_STAGED
  CHANGED_FILES_SCOPE_MARKDOWN = compose markdown:
    ## Changed Files Scope
    ### Baseline
    - RUN_BASE_REF: {{RUN_BASE_REF}}
    ### Files Changed Since Baseline
    - [each path from CHANGED_FILES_FROM_BASE, or "none"]
    ### Unstaged Changed Files
    - [each path from CHANGED_FILES_UNSTAGED, or "none"]
    ### Staged Changed Files
    - [each path from CHANGED_FILES_STAGED, or "none"]
    ### Review Scope Files
    - [each path from CHANGED_FILES_SCOPE, or "none"]

  # B) Standards review pass runs before standards-only coding
  {tools.invoke_coding_standards_reviewer}

  STANDARDS_REVIEW_FAILURE_REPORT = collect coding-standards-reviewer failure when it reports failure,
  returns no run summary, reports run_status=incomplete, fails to confirm stored_result=yes,
  or fails to confirm stored reviewer result.

  IF STANDARDS_REVIEW_FAILURE_REPORT is not empty:
    Display: "Coding standards reviewer failure detected. Restarting reviewer once."
    Close the failed coding-standards-reviewer subagent handle if the runtime exposes one.
    Restart coding-standards-reviewer with the same invocation inputs and same REVIEW_ITERATION.
    {tools.invoke_coding_standards_reviewer}

    STANDARDS_RESTART_FAILURE_REPORT = collect restarted coding-standards-reviewer failure when it reports failure,
    returns no run summary, reports run_status=incomplete, fails to confirm stored_result=yes,
    or fails to confirm stored reviewer result.

    IF STANDARDS_RESTART_FAILURE_REPORT is not empty:
      Display: "Coding standards reviewer restart failed. Rerunning the full standards review once."
      Rerun coding-standards-reviewer with the same invocation inputs and same REVIEW_ITERATION.
      The rerun intentionally reuses REVIEW_ITERATION because reviewer-result storage upserts by loop, iteration, and reviewer.
      {tools.invoke_coding_standards_reviewer}

      STANDARDS_FULL_RERUN_FAILURE_REPORT = collect rerun coding-standards-reviewer failure when it reports failure,
      returns no run summary, reports run_status=incomplete, fails to confirm stored_result=yes,
      or fails to confirm stored reviewer result.

      IF STANDARDS_FULL_RERUN_FAILURE_REPORT is not empty:
        ERROR: "Coding standards reviewer failed after bounded recovery"
        DIAGNOSTIC: compose detailed report containing:
        - initial STANDARDS_REVIEW_FAILURE_REPORT
        - restart STANDARDS_RESTART_FAILURE_REPORT
        - full rerun STANDARDS_FULL_RERUN_FAILURE_REPORT
        - review iteration, failed step/stage, tool/command in use,
          prompt/invocation inputs, exact error output, retry/fallback response,
          storage status, and recommended orchestrator action from the reviewer
        FAIL-CLOSED:
        - Do NOT call consolidate_review_cycle
        - Do NOT call decide_standards_action
        - Do NOT invoke respec-commit
        EXIT: Workflow terminated

  # C) Consolidate standards reviewer result
  LOOP_ID = STANDARDS_LOOP_ID
  ACTIVE_REVIEWERS = ["coding-standards-reviewer"]
  CONSOLIDATION_RESPONSE = {tools.consolidate_review_cycle}
  IF consolidate_review_cycle reports failure:
    ERROR: "Phase 2 review consolidation failed"
    DIAGNOSTIC: [surface the exact MCP/tool error]
    FAIL-CLOSED:
    - Do NOT call decide_standards_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  IF CONSOLIDATION_RESPONSE.iteration != REVIEW_ITERATION:
    ERROR: "Phase 2 review consolidation iteration mismatch"
    DIAGNOSTIC: [surface CONSOLIDATION_RESPONSE and REVIEW_ITERATION]
    FAIL-CLOSED:
    - Do NOT call decide_standards_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  # D) Retrieve consolidated standards feedback
  STANDARDS_FEEDBACK = {tools.get_standards_feedback}
  IF STANDARDS_FEEDBACK is empty OR retrieval fails:
    ERROR: "Phase 2 consolidated feedback missing"
    DIAGNOSTIC: [surface the exact MCP/tool error]
    FAIL-CLOSED:
    - Do NOT call decide_standards_action
    - Do NOT invoke respec-commit
    EXIT: Workflow terminated

  # E) Decide whether standards-only coding is required
  STANDARDS_DECISION_RESPONSE = {tools.decide_standards_action}
  STANDARDS_DECISION = STANDARDS_DECISION_RESPONSE.status
  STANDARDS_SCORE = STANDARDS_DECISION_RESPONSE.current_score
  STANDARDS_ITERATION = STANDARDS_DECISION_RESPONSE.iteration

  ═══════════════════════════════════════════════
  MANDATORY STANDARDS LOOP LIMIT
  ═══════════════════════════════════════════════
  Maximum standards loop iterations: 5

  IF STANDARDS_ITERATION >= 5 AND STANDARDS_DECISION == "refine":
    STANDARDS_DECISION = "user_input"
    Force "user_input" path — present feedback and wait for user guidance
    Display: "⚠ Standards loop reached iteration limit (5)"
  ═══════════════════════════════════════════════

  IF STANDARDS_DECISION == "completed":
    Display: "🟣 [Phase 2 · Complete] ✅ Rubric Score: {{STANDARDS_SCORE}}/100 — ready for completion gate (threshold met, no active blockers)"
    exit loop

  IF STANDARDS_DECISION == "refine":
    REVIEWER_FEEDBACK_CONTEXT_MARKDOWN = {tools.get_reviewer_feedback_context}
    IF REVIEWER_FEEDBACK_CONTEXT_MARKDOWN is empty OR retrieval fails:
      ERROR: "Phase 2 reviewer feedback context missing"
      DIAGNOSTIC: [surface the exact MCP/tool error]
      FAIL-CLOSED:
      - Do NOT invoke standards-only coder
      - Do NOT invoke respec-commit
      EXIT: Workflow terminated
    Treat REVIEWER_FEEDBACK_CONTEXT_MARKDOWN as the primary standards action list.
    Instruct the coder to retrieve full reviewer markdown from reviewer_results only when a point needs original rationale/citations.

    {tools.invoke_coder_standards}
    IF coder reports failure:
      ERROR: "Standards coder failed"
      DIAGNOSTIC: [surface the exact coder error/output]
      FAIL-CLOSED:
      - Do NOT invoke respec-commit
      EXIT: Workflow terminated

    # Loop commits are progress checkpoints only.
    # Completion commit is owned by Step 8.5 finalization gate.
    COMMIT_KIND = "phase2-checkpoint"
    COMMIT_WORKFLOW_KIND = "code"
    ALLOW_EMPTY = true
    {tools.commit_command_invocation}

    STANDARDS_REVIEW_ITERATION = STANDARDS_ITERATION + 1
    Display: "🟣 [Phase 2 · Iteration {{STANDARDS_ITERATION}}] ⟳ Rubric Score: {{STANDARDS_SCORE}}/100 — decision={{STANDARDS_DECISION}}; refining standards"
    continue loop

  IF STANDARDS_DECISION == "user_input":
    STANDARDS_FEEDBACK = {tools.get_standards_feedback}
    Display stagnation info with: phase 1 score, phase 2 current score, iterations, key issues

    {selection_prompt_instructions}
      1. Continue Phase 2 with more iterations
      2. Finalize current standards state now

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 7.5. Branch on the selected option. Continue with the matching standards action immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

    Store user choice and branch accordingly:
    - Option 1: REVIEWER_FEEDBACK_CONTEXT_MARKDOWN = {tools.get_reviewer_feedback_context}
                IF REVIEWER_FEEDBACK_CONTEXT_MARKDOWN is empty OR retrieval fails:
                  ERROR: "Phase 2 reviewer feedback context missing"
                  DIAGNOSTIC: [surface the exact MCP/tool error]
                  FAIL-CLOSED:
                  - Do NOT invoke standards-only coder
                  - Do NOT invoke respec-commit
                  EXIT: Workflow terminated
                Treat REVIEWER_FEEDBACK_CONTEXT_MARKDOWN as the primary standards action list.
                Instruct the coder to retrieve full reviewer markdown from reviewer_results only when a point needs original rationale/citations.
                {tools.invoke_coder_standards}
                IF coder reports failure:
                  ERROR: "Standards coder failed"
                  DIAGNOSTIC: [surface the exact coder error/output]
                  FAIL-CLOSED:
                  - Do NOT invoke respec-commit
                  EXIT: Workflow terminated
                COMMIT_KIND = "phase2-checkpoint"
                COMMIT_WORKFLOW_KIND = "code"
                ALLOW_EMPTY = true
                {tools.commit_command_invocation}
                STANDARDS_REVIEW_ITERATION = STANDARDS_ITERATION + 1
                continue loop
    - Option 2: FINALIZATION_DECISION_SOURCE = "phase2-user-finalized"
                EXIT Phase 2 loop → Step 8.5
```

#### Step 7.5.3: Exit to Completion Gate

```text
IF STANDARDS_DECISION == "completed":
  FINALIZATION_DECISION_SOURCE = "phase2-complete"
  Proceed to Step 8.5 (Completion Gate)
```

### 8.5 Completion Gate (Mandatory)

```text
# Ensure source label exists for completion metadata.
IF FINALIZATION_DECISION_SOURCE is empty:
  FINALIZATION_DECISION_SOURCE = "loop-complete"

COMPLETION_GATE_STATUS = "passed"
COMPLETION_GATE_SUMMARY = "pre-commit run -a passed."

# Enforce repository hooks exactly once before final completion commit.
PRECOMMIT_EXIT_CODE = run: pre-commit run -a

IF PRECOMMIT_EXIT_CODE != 0:
  Display: "❌ Completion gate failed: pre-commit hooks reported issues."
  Display: "Finalization is non-compliant until hooks pass."
  Display: "Classify the failure from the hook transcript before branching."

  COMPLETION_GATE_FAILURE_KIND = classify from hook transcript as exactly one of:
    - "actionable_repo_issue"
    - "external_blocker"

  Classification rules:
  - Use "actionable_repo_issue" when the failure is fixable by repository changes the workflow owns:
    formatting/import rewrites, lint failures, type-check failures, test failures,
    terraform fmt changes, generated-file drift, missing repo configuration, or any hook
    output that points to code/config/content changes inside the workspace.
  - Use "external_blocker" only when the failure is outside repo control and cannot be
    resolved by another refinement pass:
    missing API keys/credentials, unavailable external services, network outages, rate
    limits, or missing system prerequisites the workflow does not provision.

  COMPLETION_GATE_FAILURE_SUMMARY = [one concise sentence quoting the concrete blocker]

  IF COMPLETION_GATE_FAILURE_KIND == "actionable_repo_issue":
    USER_FEEDBACK_MARKDOWN = "Completion gate failed; automatic refine due to actionable hook failure in mode={{RESOLVED_MODE}}. Blocker: {{COMPLETION_GATE_FAILURE_SUMMARY}}"
    LOOP_ID = (
      STANDARDS_LOOP_ID if "coding-standards-reviewer" in ACTIVE_REVIEWERS
      else CODING_LOOP_ID
    )
    {tools.store_user_feedback}
    Display: "↩ Returning to refinement automatically: {{COMPLETION_GATE_FAILURE_SUMMARY}}"
    IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
      Return to Step 7.5.2
    ELSE:
      Return to Step 7.4

  IF COMPLETION_GATE_FAILURE_KIND == "external_blocker":
    COMPLETION_GATE_STATUS = "deferred-external-blocker"
    COMPLETION_GATE_SUMMARY = {{COMPLETION_GATE_FAILURE_SUMMARY}}
    FINALIZATION_DECISION_SOURCE = "{{FINALIZATION_DECISION_SOURCE}}+external-gate-deferred"
    Display: "⚠ Proceeding to final completion commit with deferred external blocker: {{COMPLETION_GATE_FAILURE_SUMMARY}}"

# pre-commit sometimes rewrites tracked files or adds cleanup-only changes.
# Treat any resulting diffs as part of the final workflow output.
# Do not question or call out these changes; stage the full tree and commit it.
# pre-commit succeeded; compose dedicated completion commit.
IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
  FINAL_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=STANDARDS_LOOP_ID, count=1)
  FINAL_LOOP_LABEL = "Phase 2 standards"
  FINAL_LOOP_ID = STANDARDS_LOOP_ID
  FINAL_SOURCE = "coding-standards-reviewer CriticFeedback"
ELSE:
  FINAL_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=CODING_LOOP_ID, count=1)
  FINAL_LOOP_LABEL = "Phase 1"
  FINAL_LOOP_ID = CODING_LOOP_ID
  FINAL_SOURCE = "MCP consolidated CriticFeedback"

COMMIT_KIND = "final"
COMMIT_WORKFLOW_KIND = "code"
ALLOW_EMPTY = true
{tools.commit_command_invocation}

Proceed directly to Step 9 (Integration & Documentation)
```

### 9. Integration & Documentation
Complete implementation workflow and update Phase:

#### Generate Implementation Summary
```text
Retrieve final state:
- Phase: {tools.get_phase_document}
- Final Feedback: {tools.get_feedback}

Generate IMPLEMENTATION_SUMMARY including:
- Code Quality Score: {{CODE_QUALITY_SCORE}}%
- Test Results: {{TEST_RESULTS from CriticFeedback}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Files Modified: {{FILE_COUNT}}
- Commit Summary: {{GIT_LOG_SUMMARY}}
```

#### Apply Design Conformance Write-Back

Applies only when "design-conformance-reviewer" ran this Phase (see Step 6.6). Without this step the
`### Skeleton Index` silently becomes a lie the moment a confirmed-legitimate deviation is implemented —
see docs/phase-refactor/decisions.md "Deviation is classified and written back, not enforced".

```text
IF "design-conformance-reviewer" in ACTIVE_REVIEWERS:
  WRITE_BACK_MARKDOWN = {tools.get_design_conformance_write_back}
  IF WRITE_BACK_MARKDOWN is present:
    UPDATED_SKELETON_INDEX = [extract "### Updated Skeleton Index" content from WRITE_BACK_MARKDOWN]
    NEW_SETTLED_DECISIONS = [extract "### New Settled Decisions" content from WRITE_BACK_MARKDOWN]
    IF UPDATED_SKELETON_INDEX is non-empty:
      PHASE_MARKDOWN's "### Skeleton Index" = UPDATED_SKELETON_INDEX
    IF NEW_SETTLED_DECISIONS is non-empty:
      Append NEW_SETTLED_DECISIONS to PHASE_MARKDOWN's "### Settled Design Decisions"
    # Only these two sections are touched. "### Module Layout" and "### Collaboration And Wiring"
    # are never rewritten here -- a divergence large enough to invalidate them is a Shape Amendment
    # Request routed back to respec-phase, per docs/phase-refactor/phase-7-conformance.md.
```

#### Update Phase
```text
Update Phase status and implementation details using {tools.store_phase_document}:

Status: "IMPLEMENTED"
Implementation Summary: {{IMPLEMENTATION_SUMMARY}}
Code Quality: {{CODE_QUALITY_SCORE}}%
Test Coverage: {{COVERAGE_PERCENTAGE}}%
Implementation Date: {{CURRENT_DATE}}
```

#### Report Completion
```text
Present final summary:
"✓ Implementation complete for {{PHASE_NAME}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Type Checker: {{TYPE_CHECKER_STATUS}}
- Linter: {{LINTER_STATUS}}

Implementation artifacts:
- Implementation Plan: {{IMPLEMENTATION_PLAN_PATH}}
- Phase: Available via phase_loop_id={{PHASE_LOOP_ID}}
- Code Review: Available via coding_loop_id={{CODING_LOOP_ID}}
- Commits: {{COMMIT_COUNT}} commits with test results
- Completion Gate: {{COMPLETION_GATE_STATUS}} — {{COMPLETION_GATE_SUMMARY}}
- Phase Status: Updated via {tools.store_phase_document}

Ready for deployment."
```

"""
