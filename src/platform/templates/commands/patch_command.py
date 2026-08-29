from src.platform.models import PatchCommandTools


def generate_patch_command_template(tools: PatchCommandTools) -> str:
    selection_prompt_instructions = tools.tui_adapter.selection_prompt_instruction
    selection_response_source = tools.tui_adapter.selection_response_source
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [request]
description: Update existing code through amendment tasks with full quality review
---

# respec-patch Command: Maintenance Orchestration

## Overview
Orchestrate bug fixes, feature extensions, and refactoring of existing code through amendment tasks with the same quality scoring, review loops, and documentation trail as respec-code.

{tools.mcp_tools_reference}

{tools.tui_adapter.subagent_invocation_guardrail}

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed above.

When instructions say "CALL tool_name", execute the tool:
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
- Resolve execution mode, Phase, amendment scope, and active reviewers
- CALL MCP tools
- Invoke specialized agents
- Consolidate review results
- Run git, commit, and pre-commit orchestration
- Update Phase evolution log and workflow documentation artifacts

Forbidden command responsibilities:
- Do NOT directly edit source code.
- Do NOT directly edit tests.
- Do NOT manually implement the requested patch.
- Do NOT substitute command-local implementation for a missing or failed coder agent.

Implementation responsibility:
- ALL source-code and test implementation MUST be delegated to `respec-coder`.
- If `respec-coder` cannot be invoked, fail closed with diagnostics.
- If `respec-coder` fails, follow the coder failure branch; do not continue by implementing code in this command.
═══════════════════════════════════════════════

## Workflow Steps

### 1. Parse User Inputs

```text
PLAN_NAME = [first argument from command - the project name]
RAW_REQUEST = [all remaining input after PLAN_NAME]
```

#### Step 1.1: Initialize Workflow Variables

```text
PATCH_REQUEST_BRIEF = [normalized request produced after clarification]
REQUEST_SUMMARY = [one-line summary produced from PATCH_REQUEST_BRIEF]
GUIDANCE_DOCUMENT_PATHS = []
```

Fail closed on ambiguity:
- Treat RAW_REQUEST as the only user-authored source of truth for the patch.
- Do NOT assume RAW_REQUEST has a clean internal boundary between "the change"
  and "extra context".
- Do NOT derive execution inputs from an ambiguous RAW_REQUEST.
- Ask a clarifying question or present options whenever multiple reasonable
  interpretations would change scope, target area, implementation direction,
  validation criteria, active-plan selection, or phase selection.
- Do NOT invoke the patch planner until the request is sufficiently clear.

Once RAW_REQUEST is sufficiently clear:
- Normalize it into PATCH_REQUEST_BRIEF containing:
  - requested change
  - relevant supporting context and constraints
  - resume details or file references that must be preserved
  - guidance document paths from GUIDANCE_DOCUMENT_PATHS under a clear `Guidance Document Paths` subsection
  - any clarified decisions that subagents must treat as settled
- Derive REQUEST_SUMMARY as a short one-line summary for commit/final reporting.

Guidance document path handling:
- If RAW_REQUEST contains readable project-local document paths intended to guide the patch
  (for example `.md`, `.txt`, `.rst`, or `.adoc` files), add each path to GUIDANCE_DOCUMENT_PATHS.
- Guidance document paths are read-only context for subagents. They are not implementation files
  to edit unless the clarified patch request explicitly says to edit that file.
- Validate each guidance document path before invoking subagents:
  - Relative paths are resolved from the target project working directory.
  - Paths MUST stay inside the target project working directory.
  - Paths MUST exist and be readable.
  - Invalid or outside-project paths are preserved in PATCH_REQUEST_BRIEF as reported user intent,
    but are NOT passed as readable guidance paths; ask for clarification if the missing path
    changes scope, target area, or implementation direction.
- Do NOT block solely because a valid project-local guidance document is outside `.respec-ai`.
  Preserve the boundary by passing the path to subagents and requiring read-only use.

#### Step 1.2: Capture Execution Mode (MANDATORY)

```text
IF RAW_REQUEST already contains one unambiguous execution mode token:
  EXECUTION_MODE = [normalize explicit token to MVP|hardening]
  EXECUTION_MODE_SOURCE = "raw-request"
ELSE:
  {selection_prompt_instructions}
    Header: "Patch Mode"
    Question: "Select the delivery intent for this patch."
    multiSelect: false
    Options:
      - MVP: Prioritize core functional/spec delivery, defer non-P0 hardening
      - hardening: Prioritize full quality hardening and strict review

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 1.2. Set EXECUTION_MODE. Continue to Step 1.3 immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  EXECUTION_MODE = [selected option label normalized to MVP|hardening]
  EXECUTION_MODE_SOURCE = "patch-mode-selection"

Display: "Execution mode selected: {{EXECUTION_MODE}}"
```

#### Step 1.3: Resolve Active Plan (if referenced)

```text
IF RAW_REQUEST references an active plan (e.g., "use the active plan",
   "from plan mode", or contains a path to a .md file in {tools.plans_dir}/):

  PLAN_FILE_PATH = [extract or infer path from RAW_REQUEST]
  IF PLAN_FILE_PATH not explicitly provided:
    PLAN_FILE_PATH = Glob({tools.plans_dir}/*.md) → select most recently modified

  PLAN_CONTENT = Read(PLAN_FILE_PATH)

  Display: "Using active plan: {{basename of PLAN_FILE_PATH}}"

  PATCH_REQUEST_BRIEF = compose normalized brief from:
    - plan content as primary requested work
    - guidance document path: PLAN_FILE_PATH
    - `Guidance Document Paths` subsection containing PLAN_FILE_PATH and any other validated paths from RAW_REQUEST
    - any explicit constraints or resume instructions present in RAW_REQUEST
  GUIDANCE_DOCUMENT_PATHS.append(PLAN_FILE_PATH)
  REQUEST_SUMMARY = [short summary derived from PATCH_REQUEST_BRIEF]

ELIF recent system message contains "exited Plan Mode" with a plan file path:
  PLAN_FILE_PATH = [path from system message]
  PLAN_CONTENT = Read(PLAN_FILE_PATH)

  Display: "Detected active plan from plan mode: {{basename of PLAN_FILE_PATH}}"

  PATCH_REQUEST_BRIEF = compose normalized brief from:
    - plan content as primary requested work
    - guidance document path: PLAN_FILE_PATH
    - `Guidance Document Paths` subsection containing PLAN_FILE_PATH and any other validated paths from RAW_REQUEST
    - any explicit constraints or resume instructions present in RAW_REQUEST
  GUIDANCE_DOCUMENT_PATHS.append(PLAN_FILE_PATH)
  REQUEST_SUMMARY = [short summary derived from PATCH_REQUEST_BRIEF]

ELSE:
  IF RAW_REQUEST is empty or whitespace only:
    ERROR: "Patch request is required after PLAN_NAME."
    EXIT

  IF RAW_REQUEST remains ambiguous after initial read:
    {selection_prompt_instructions}
      Header: "Clarify Patch Request"
      Question: "Which interpretation matches the patch you want?"
      Options: [2-4 concrete options derived from plausible interpretations]
    OR ask one direct clarifying question when options are not cleaner.

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 1.3. Clarify RAW_REQUEST. Continue with PATCH_REQUEST_BRIEF normalization immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

  PATCH_REQUEST_BRIEF = compose normalized brief from the clarified RAW_REQUEST:
    - requested change
    - constraints and supporting context
    - affected area, if known
    - `Guidance Document Paths` subsection containing each validated path from GUIDANCE_DOCUMENT_PATHS, or "None"
    - resume details, if any
    - clarified decisions that downstream agents must honor
  REQUEST_SUMMARY = [short summary derived from PATCH_REQUEST_BRIEF]
```

### 2. Phase Resolution

#### Step 2.1: Discover all phases

```text
ALL_PHASES = {tools.list_all_phases}

IF count(ALL_PHASES) == 0:
  ERROR: "No phases found in project {{PLAN_NAME}}"
  SUGGEST: "Run roadmap workflow first to create phases"
  {tools.roadmap_command_invocation}
  EXIT
```

#### Step 2.2: Single phase shortcut

```text
IF count(ALL_PHASES) == 1:
  PHASE_FILE_PATH = ALL_PHASES[0]
  Display: "Single phase found, auto-selected: {{basename of the parent directory of PHASE_FILE_PATH}}"
  → Skip to Step 2.4
```

#### Step 2.3: Multi-phase relevance matching

```text
For each PHASE_FILE in ALL_PHASES:
  Read the Overview section (Objectives, Scope, Deliverables) — first 30 lines
  Assess relevance of PATCH_REQUEST_BRIEF to this phase's content

Rank phases by relevance to PATCH_REQUEST_BRIEF.

IF clear best match (one phase strongly relevant, others weak):
  PHASE_FILE_PATH = best match
  Display: "Auto-detected phase: {{basename of the parent directory of PHASE_FILE_PATH}}"
  Display: "Reason: [brief explanation of why this phase matches]"
  IF other phases have partial relevance:
    Display: "Note: This change also touches concerns from: [other phase names]"
ELSE:
  {selection_prompt_instructions}
    Question: "Which phase does this patch belong to? '{{REQUEST_SUMMARY}}'"
    Header: "Select Phase for Patch"
    multiSelect: false
    Options: [ranked phases with objectives summary as description]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 2.3. Set PHASE_FILE_PATH. Continue to Step 2.4 immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  PHASE_FILE_PATH = [selected from response]
```

#### Step 2.4: Extract canonical name and sync to MCP

```text
PHASE_NAME = [basename of the parent directory of PHASE_FILE_PATH]

Display to user: "Located phase file: {{PHASE_NAME}}"

{tools.sync_phase_instructions}
```

**Important**:
- PLAN_NAME is used for all MCP storage operations
- PHASE_NAME is the canonical name extracted from file path
- All subsequent operations use PHASE_NAME (canonical)

### 3. Scope the Amendment

Single-shot amendment scoping — no refinement loop or critic. patch-planner
explores the codebase once and produces an amendment scope block; there is
nothing left to iterate against without a critic, so a failed or incomplete
result fails closed and directs the user to re-run `respec-patch`.

#### Step 3.1: Initialize Phase Loop and Store Execution Intent Snapshot

```text
PHASE_LOOP_ID = {tools.initialize_phase_loop}

LOOP_ID = PHASE_LOOP_ID
USER_FEEDBACK_MARKDOWN = (
  "## Execution Intent Snapshot\\n"
  + "- Mode: {{EXECUTION_MODE}}\\n"
  + "- Source: patch-mode-selection\\n"
  + "- Tie-Break Policy: Prioritize core functional/spec delivery unless active P0 risks demand otherwise.\\n"
  + "- Deferred Risk Register Source: Amendment Scope Acceptance Criteria"
)
{tools.store_user_feedback}
```

#### Step 3.2: Link Phase Loop to Phase

```text
{tools.link_phase_loop}
```

#### Step 3.3: Invoke Patch Planner Agent and Verify Amendment Scope Storage

{tools.invoke_patch_planner}

```text
IF patch-planner reports failure:
  ERROR: "Patch planner failed"
  DIAGNOSTIC: [surface the exact planner error/output]
  FAIL-CLOSED:
  - Do NOT continue to Step 4
  EXIT: Workflow terminated

IF patch-planner output contains exact marker `PHASE_AMENDMENT_REQUIRED`:
  STATUS: "Phase amendment required before patch coding"
  DIAGNOSTIC: [surface the planner Rationale, Evidence, and Next Step]
  FAIL-CLOSED:
  - Do NOT retrieve AMENDMENT_SCOPE_MARKDOWN
  - Do NOT continue into code reconnaissance, implementation, review, commit, or Phase Evolution Log update
  EXIT: Workflow paused; run the Phase refinement workflow (`respec-phase`) before resuming patch work

AMENDMENT_SCOPE_MARKDOWN = {tools.get_amendment_scope}

IF AMENDMENT_SCOPE_MARKDOWN not found or retrieval fails:
  ERROR: "Patch planner did not produce a retrievable amendment scope"
  DIAGNOSTIC: [surface the exact retrieval error/output]
  FAIL-CLOSED:
  - Do NOT continue to Step 4
  EXIT: Workflow terminated; re-run respec-patch to retry scoping

Display: "✅ Amendment scoped: {{AMENDMENT_NAME}}"
```

### 4. Mode Extraction + Reviewer Resolution

Parse the amendment scope to determine which specialist reviewers to activate:

#### Step 4.1: Validate Resolved Mode Against Amendment Scope Policy

```text
# REUSE AMENDMENT_SCOPE_MARKDOWN from Step 3.3 (do not re-retrieve)

AMENDMENT_MODE = extract from AMENDMENT_SCOPE_MARKDOWN:
  "### Acceptance Criteria > #### Execution Intent Policy > Mode"

IF AMENDMENT_MODE in {{MVP,hardening}} AND AMENDMENT_MODE != EXECUTION_MODE:
  {selection_prompt_instructions}
    Header: "Mode Mismatch"
    Question: "Amendment scope's policy mode differs from selected patch mode. Select the mode for this loop."
    Options: selected patch mode, amendment scope policy mode
  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 4.1. Set EXECUTION_MODE. Continue to the resolved-mode display immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.
  EXECUTION_MODE = [user-selected mode]
  EXECUTION_MODE_SOURCE = "amendment-scope-policy-mismatch-resolution"

IF AMENDMENT_MODE missing or unsupported:
  # Keep user-selected mode as source of truth.
  EXECUTION_MODE = EXECUTION_MODE

Display: "Resolved execution mode: {{EXECUTION_MODE}} (source: {{EXECUTION_MODE_SOURCE}})"
```

#### Step 4.2: Extract Step Modes

```text
STEP_MODES = set()
STEP_DOMAINS = {{}}  # Step number -> "frontend" | "backend", for coder dispatch (does not affect STEP_MODES / reviewer rostering below)

For each "#### Step N:" section in AMENDMENT_SCOPE_MARKDOWN:
  Scan Step content for mode indicators:
  IF contains frontend keywords (UI, component, template, CSS, accessibility, HTMX, React, Vue):
    STEP_MODES.add("frontend")
  IF contains API keywords (endpoint, REST, route, request, response, authentication, middleware):
    STEP_MODES.add("api")
  IF contains database keywords (schema, migration, model, query, index, SQL, ORM):
    STEP_MODES.add("database")
  IF contains infrastructure keywords (Docker, CI/CD, deployment, container, pipeline, environment):
    STEP_MODES.add("infrastructure")

  # Classify this Step for coder dispatch: file paths named in the Step are a stronger
  # signal than prose keywords, so prefer them; fall back to the same keyword scan.
  IF the Step names file paths matching frontend locations (templates/, static/, components/, frontend-flavored extensions):
    STEP_DOMAINS[N] = "frontend"
  ELSE IF the Step names file paths matching non-frontend (backend) locations:
    STEP_DOMAINS[N] = "backend"
  ELSE IF Step content matched frontend keywords above:
    STEP_DOMAINS[N] = "frontend"
  ELSE:
    STEP_DOMAINS[N] = "backend"

Display: "Detected step modes: {{STEP_MODES}}"
Display: "Detected coder dispatch per Step: {{STEP_DOMAINS}}"
```

#### Step 4.3: Resolve Active Reviewers

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

# Amendments diverge from a Phase's design record at least as often as initial
# implementations, so the same conformance check applies here.
PHASE_MARKDOWN = {tools.get_phase_document}
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

WORKFLOW_GUIDANCE_MARKDOWN = compose markdown from PATCH_REQUEST_BRIEF:
  ## Workflow Guidance
  ### Guidance Summary
  [normalized request summary from PATCH_REQUEST_BRIEF, otherwise "None"]
  ### Guidance Document Paths
  - [each validated path from GUIDANCE_DOCUMENT_PATHS]
  - None
  ### Constraints
  - [constraint or supporting context preserved from PATCH_REQUEST_BRIEF]
  - None
  ### Resume Context
  - [resume detail or file reference from PATCH_REQUEST_BRIEF]
  - None
  ### Settled Decisions
  - [clarified user decisions from PATCH_REQUEST_BRIEF]
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
#   PHASE_LOOP_ID     — loop linked to the Phase document (Step 3)
#   CODING_LOOP_ID    — Phase 1 functional loop (AQC + spec-alignment + domains)
#   STANDARDS_LOOP_ID — Phase 2 standards loop (coding-standards-reviewer only)

PHASE1_REVIEWERS = ACTIVE_REVIEWERS excluding "coding-standards-reviewer"
(coding-standards-reviewer runs in Phase 2 only)

Display: "Active reviewers: {{ACTIVE_REVIEWERS}}"
Display: "Phase 1 reviewers: {{PHASE1_REVIEWERS}}"
```

### 5. Coding Loop (Implementation + Review)

#### Step 5.1: Initialize Coding Loop

```text
CODING_LOOP_ID = {tools.initialize_coding_loop}

LOOP_ID = CODING_LOOP_ID
USER_FEEDBACK_MARKDOWN = (
  "## Execution Intent Snapshot\\n"
  + "- Mode: {{EXECUTION_MODE}}\\n"
  + "- Source: patch-mode-selection\\n"
  + "- Tie-Break Policy: Prioritize core functional/spec delivery unless active P0 risks demand otherwise.\\n"
  + "- Deferred Risk Register Source: Amendment Scope Acceptance Criteria"
)
{tools.store_user_feedback}
```

#### Step 5.2: CRITICAL - Dual Loop ID Management

You now have TWO active loop IDs - DO NOT confuse them:

**phase_loop_id = {{PHASE_LOOP_ID}}**
- Purpose: Identifies the loop linked to the Phase document (Step 3)
- Used by: coder and reviewers, to verify against Phase and the amendment scope
- Storage: Phase document linked to this loop

**coding_loop_id = {{CODING_LOOP_ID}}**
- Purpose: Phase 1 functional feedback
- Used by: coder (feedback retrieval), reviewers (structured result storage), MCP consolidation
- Storage: CriticFeedback for code quality

**STANDARDS_LOOP_ID** (initialized in Step 6.5.1)
- Purpose: Phase 2 standards feedback
- Used by: coder (standards-only mode), coding-standards-reviewer, MCP consolidation

Pass BOTH IDs to coding agents. Never swap them.

#### Step 5.3: Phase 1 Iteration Loop (Coder -> Reviews -> Decision -> Commit)

```text
RUN_BASE_REF = RUN_BASE_REF if defined else [result of: git rev-parse HEAD]
PHASE1_SIGNED_OFF_REVIEWERS = PHASE1_SIGNED_OFF_REVIEWERS if defined else []

Loop:
  REVIEW_ITERATION = REVIEW_ITERATION if defined else 1

  # A) Coder pass -- dispatch per Step domain (STEP_DOMAINS from Step 4.2), sequentially.
  # Both coders may run in one iteration; they are not invoked in parallel because they
  # may touch a shared file (a types module, a route table) and the fan-out policies are
  # built for independent workers collecting into a parent, which coders are not.
  ACTIVE_CODER_DOMAINS = set(STEP_DOMAINS.values()) if STEP_DOMAINS else {{"backend"}}
  CODER_REPORTS = []

  IF "backend" in ACTIVE_CODER_DOMAINS:
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
    CODER_REPORTS.append(the backend coder's Iteration Handoff report)

  IF "frontend" in ACTIVE_CODER_DOMAINS:
    {tools.invoke_frontend_coder}
    IF coder reports failure:
      ERROR: "Frontend coder failed"
      DIAGNOSTIC: [surface the exact coder error/output]
      FAIL-CLOSED:
      - Do NOT invoke reviewers
      - Do NOT call consolidate_review_cycle
      - Do NOT call decide_coding_action
      - Do NOT invoke respec-commit
      EXIT: Workflow terminated
    CODER_REPORTS.append(the frontend coder's Iteration Handoff report)

  # Merge CODER_REPORTS into one report for commit orchestration and reviewer context; see
  # respec-code's Step 7.4 merge rule (concatenate list fields, worst-case status fields,
  # sum numeric fields). A single report passes through unchanged.
  MERGED_CODER_REPORT = merge(CODER_REPORTS) per the rule above

  # B) Phase 1 review team orchestration
  PHASE1_REVIEWERS_TO_INVOKE = []
  PHASE1_INVALIDATED_REVIEWERS = []

  Set PHASE1_INVALIDATED_REVIEWERS by applying these rules to each reviewer in PHASE1_SIGNED_OFF_REVIEWERS:
  - Compare MERGED_CODER_REPORT, changed files, amendment-scope context changes, patch scope changes,
    and prior consolidated feedback.
  - Add a signed-off reviewer when new or changed work touches that reviewer's responsibility.
  - Add all Phase 1 reviewers when the amendment scope, Phase document, execution mode, public behavior,
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

  IF "frontend-reviewer" in PHASE1_REVIEWERS_TO_INVOKE:
    # Belt-and-braces (B9): the reviewer's own contract already tears down via
    # `frontend-preflight --stop` before it stores its result, but a crashed or restarted
    # reviewer must not leak a dev server. Safe to call even when nothing is running.
    RUN (Bash): respec-ai frontend-preflight --stop

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
  - NEVER add "frontend-reviewer" to PHASE1_SIGNED_OFF_REVIEWERS regardless of score or blockers.
    Its input is the rendered application: a transitive change elsewhere (a shared token, a
    component, an API response shape) can break the UI without touching a frontend file, and a
    stale sign-off would reuse a pass verdict that no longer holds. It re-runs every iteration.

  # C) MCP coding decision
  CODING_DECISION_RESPONSE = {tools.decide_coding_action}
  CODING_DECISION = CODING_DECISION_RESPONSE.status
  CODING_SCORE = CODING_DECISION_RESPONSE.current_score
  CODING_ITERATION = CODING_DECISION_RESPONSE.iteration
  Decision options: "completed", "refine", "user_input"

  # D) Phase 1 commit orchestration (every pass)
  # Loop commits are progress checkpoints only.
  # Completion commit is owned by Step 6.7 finalization gate.
  COMMIT_KIND = "phase1-checkpoint"
  COMMIT_WORKFLOW_KIND = "patch"
  ALLOW_EMPTY = true
  {tools.commit_command_invocation}

  # E) Decision handling after commit
  IF CODING_DECISION == "refine":
    REVIEW_ITERATION = CODING_ITERATION + 1
    continue loop

  IF CODING_DECISION == "completed":
    exit loop to Step 6

  IF CODING_DECISION == "user_input":
    exit loop to Step 6
```

### 6. Coding Decision Handling

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

```text
IF CODING_DECISION == "refine":
  Display: "🔵 [Phase 1 · Iteration {{CODING_ITERATION}}] ⟳ Rubric Score: {{CODING_SCORE}}/100 — decision={{CODING_DECISION}}; refining"
  Return to Step 5.3 (next loop pass runs coder -> reviews -> decision -> commit).

ELIF CODING_DECISION == "completed":
  Display: "🔵 [Phase 1 · Complete] ✅ Rubric Score: {{CODING_SCORE}}/100 — ready for next phase (threshold met, no active blockers)"
  IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS: Proceed to Step 6.5
  ELSE:
    FINALIZATION_DECISION_SOURCE = "phase1-complete"
    Proceed to Step 6.7

ELIF CODING_DECISION == "user_input":
  LATEST_FEEDBACK = {tools.get_feedback}

  Display LATEST_FEEDBACK to user with:
  - Current rubric score and iteration
  - Key issues requiring attention
  - Recommended improvements

  Ask the user for implementation guidance.
  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 6. Store the guidance with {tools.store_user_feedback}. Continue with the next refinement pass immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  Store user feedback: {tools.store_user_feedback}
  REVIEW_ITERATION = CODING_ITERATION + 1
  Return to Step 5.3
```

### 6.5: Standards Finalization Phase

═══════════════════════════════════════════════
MANDATORY PHASE 2 ACTIVATION GATE
═══════════════════════════════════════════════
Run ONLY IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS
(standards TOML files detected in Step 4.3).

IF no standards TOML files were found in .respec-ai/config/standards/:
  Skip Phase 2 entirely. Proceed directly to Step 6.7.
  Display: "ℹ️ No coding standards configured — skipping Phase 2"

Phase 2 has ZERO built-in rules. Without standards TOML files, there is
nothing to assess. Do NOT apply general coding standards.
═══════════════════════════════════════════════

#### Step 6.5.1: Initialize Standards Loop

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

#### Step 6.5.2: Standards Review Cycle

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
    Instruct each dispatched coder to retrieve full reviewer markdown from reviewer_results only when a point needs original rationale/citations.

    # Dispatch by file domain (coding-standards-reviewer findings are untagged; see
    # STANDARDS-ONLY MODE in each coder's contract). Reuses ACTIVE_CODER_DOMAINS from Step 5.3.
    IF "backend" in ACTIVE_CODER_DOMAINS:
      {tools.invoke_coder_standards}
      IF coder reports failure:
        ERROR: "Standards coder failed"
        DIAGNOSTIC: [surface the exact coder error/output]
        FAIL-CLOSED:
        - Do NOT invoke respec-commit
        EXIT: Workflow terminated
    IF "frontend" in ACTIVE_CODER_DOMAINS:
      {tools.invoke_frontend_coder_standards}
      IF coder reports failure:
        ERROR: "Standards frontend coder failed"
        DIAGNOSTIC: [surface the exact coder error/output]
        FAIL-CLOSED:
        - Do NOT invoke respec-commit
        EXIT: Workflow terminated

    # Loop commits are progress checkpoints only.
    # Completion commit is owned by Step 6.7 finalization gate.
    COMMIT_KIND = "phase2-checkpoint"
    COMMIT_WORKFLOW_KIND = "patch"
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
    After the user responds, resume at Step 6.5. Branch on the selected option. Continue with the matching standards action immediately.
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
                Instruct each dispatched coder to retrieve full reviewer markdown from reviewer_results only when a point needs original rationale/citations.
                IF "backend" in ACTIVE_CODER_DOMAINS:
                  {tools.invoke_coder_standards}
                  IF coder reports failure:
                    ERROR: "Standards coder failed"
                    DIAGNOSTIC: [surface the exact coder error/output]
                    FAIL-CLOSED:
                    - Do NOT invoke respec-commit
                    EXIT: Workflow terminated
                IF "frontend" in ACTIVE_CODER_DOMAINS:
                  {tools.invoke_frontend_coder_standards}
                  IF coder reports failure:
                    ERROR: "Standards frontend coder failed"
                    DIAGNOSTIC: [surface the exact coder error/output]
                    FAIL-CLOSED:
                    - Do NOT invoke respec-commit
                    EXIT: Workflow terminated
                COMMIT_KIND = "phase2-checkpoint"
                COMMIT_WORKFLOW_KIND = "patch"
                ALLOW_EMPTY = true
                {tools.commit_command_invocation}
                STANDARDS_REVIEW_ITERATION = STANDARDS_ITERATION + 1
                continue loop
    - Option 2: FINALIZATION_DECISION_SOURCE = "phase2-user-finalized"
                EXIT Phase 2 loop → Step 6.7
```

#### Step 6.5.3: Exit to Completion Gate

```text
IF STANDARDS_DECISION == "completed":
  FINALIZATION_DECISION_SOURCE = "phase2-complete"
  Proceed to Step 6.7
```

### 6.7 Completion Gate (Mandatory)

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
    USER_FEEDBACK_MARKDOWN = "Completion gate failed; automatic refine due to actionable hook failure in mode={{EXECUTION_MODE}}. Blocker: {{COMPLETION_GATE_FAILURE_SUMMARY}}"
    LOOP_ID = (
      STANDARDS_LOOP_ID if "coding-standards-reviewer" in ACTIVE_REVIEWERS
      else CODING_LOOP_ID
    )
    {tools.store_user_feedback}
    Display: "↩ Returning to refinement automatically: {{COMPLETION_GATE_FAILURE_SUMMARY}}"
    IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
      Return to Step 6.5.2
    ELSE:
      Return to Step 5.3

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
COMMIT_WORKFLOW_KIND = "patch"
ALLOW_EMPTY = true
{tools.commit_command_invocation}

Proceed to Step 6.5 (Apply Design Conformance Write-Back)
```

### 6.5 Apply Design Conformance Write-Back

Applies only when "design-conformance-reviewer" ran this amendment (see Step 4.3). Without this step
the `### Skeleton Index` silently becomes a lie the moment a confirmed-legitimate deviation is
implemented — see docs/phase-refactor/decisions.md "Deviation is classified and written back, not
enforced". Runs before Step 7 so the Evolution Log's byte-integrity comparison is taken against the
already-updated document, not a stale one.

```text
IF "design-conformance-reviewer" in ACTIVE_REVIEWERS:
  WRITE_BACK_MARKDOWN = {tools.get_design_conformance_write_back}
  IF WRITE_BACK_MARKDOWN is present:
    CURRENT_PHASE_MARKDOWN = {tools.get_phase_document}
    UPDATED_SKELETON_INDEX = [extract "### Updated Skeleton Index" content from WRITE_BACK_MARKDOWN]
    NEW_SETTLED_DECISIONS = [extract "### New Settled Decisions" content from WRITE_BACK_MARKDOWN]
    IF UPDATED_SKELETON_INDEX is non-empty:
      CURRENT_PHASE_MARKDOWN's "### Skeleton Index" = UPDATED_SKELETON_INDEX
    IF NEW_SETTLED_DECISIONS is non-empty:
      Append NEW_SETTLED_DECISIONS to CURRENT_PHASE_MARKDOWN's "### Settled Design Decisions"
    # Only these two sections are touched. "### Module Layout" and "### Collaboration And Wiring"
    # are never rewritten here -- a divergence large enough to invalidate them is a Shape Amendment
    # Request routed back to respec-phase, per docs/phase-refactor/phase-7-conformance.md.
    Store via {tools.store_phase_document} using CURRENT_PHASE_MARKDOWN as content.

Proceed to Step 7 (Update Phase Evolution Log)
```

### 7. Append Phase Evolution Log Only

Record the amendment in the Phase document for traceability without changing
any substantive Phase content:

```text
PHASE_MARKDOWN = {tools.get_phase_document}

# REUSE AMENDMENT_SCOPE_MARKDOWN from Step 3.3 (do not re-retrieve)
AMENDMENT_NAME = [Extract Identity > Name from AMENDMENT_SCOPE_MARKDOWN]

Build UPDATED_PHASE_MARKDOWN by appending a new entry under existing
`## Evolution Log`, or by appending a new `## Evolution Log` section at the end
of the document if none exists. This is an append-only trace update.

## Evolution Log

### {{CURRENT_DATE}}: {{REQUEST_SUMMARY}}
- Amendment Scope: {{AMENDMENT_NAME}} ({{PLAN_NAME}}/{{PHASE_NAME}})
- Code Quality Score: {{CODE_QUALITY_SCORE}}%
- Files Changed: {{FILE_LIST}}

Integrity gate before storing:
- Strip only the `## Evolution Log` section from PHASE_MARKDOWN and UPDATED_PHASE_MARKDOWN.
- The stripped documents MUST match exactly byte-for-byte.
- Research Requirements, Implementation Plan References, Design Shape, Design
  Decisions, metadata, headings, objectives, scope, architecture, success
  criteria, deliverables, and every other non-Evolution Log section MUST
  remain unchanged.

IF any non-Evolution Log content changed:
  ERROR: "Phase Evolution Log update attempted to modify substantive Phase content"
  DIAGNOSTIC: [surface the first changed non-log section]
  FAIL-CLOSED:
  - Do NOT call update_phase_document
  - Do NOT continue to Step 8
  - Direct user to run the Phase refinement workflow (`respec-phase`) for substantive Phase changes
  EXIT: Workflow paused

Store updated Phase only after integrity gate passes:
{tools.update_phase_document}
```

### 8. Report Completion

Patch never writes into implementation.md or skeletons — the amendment scope
lives only in MCP (Step 3), and the Phase Evolution Log entry above is the
only durable record on disk.

```text
Present final summary:
"Implementation complete for amendment: {{REQUEST_SUMMARY}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}

Amendment artifacts:
- Amendment Scope: {{AMENDMENT_NAME}} under {{PHASE_NAME}}
- Phase Evolution Log: Updated
- Code Review: Available via coding_loop_id={{CODING_LOOP_ID}}
- Completion Gate: {{COMPLETION_GATE_STATUS}} — {{COMPLETION_GATE_SUMMARY}}

Ready for deployment."
```

"""
