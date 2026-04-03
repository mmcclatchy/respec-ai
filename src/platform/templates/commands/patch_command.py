from src.platform.models import PatchCommandTools


def generate_patch_command_template(tools: PatchCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [change-description]
description: Update existing code through amendment tasks with full quality review
---

# respec-patch Command: Maintenance Orchestration

## Overview
Orchestrate bug fixes, feature extensions, and refactoring of existing code through amendment tasks with the same quality scoring, review loops, and documentation trail as respec-code.

{tools.mcp_tools_reference}

## Workflow Steps

### 1. Parse Arguments

```text
PLAN_NAME = [first argument from command - the project name]
CHANGE_DESCRIPTION = [all remaining arguments - description of the change needed]
```

#### Step 1.1: Resolve Active Plan (if referenced)

```text
IF CHANGE_DESCRIPTION references an active plan (e.g., "use the active plan",
   "from plan mode", or contains a path to a .md file in {tools.plans_dir}/):

  PLAN_FILE_PATH = [extract or infer path from CHANGE_DESCRIPTION]
  IF PLAN_FILE_PATH not explicitly provided:
    PLAN_FILE_PATH = Glob({tools.plans_dir}/*.md) → select most recently modified

  PLAN_CONTENT = Read(PLAN_FILE_PATH)

  Display: "Using active plan: {{basename of PLAN_FILE_PATH}}"

  CHANGE_DESCRIPTION = PLAN_CONTENT

ELIF recent system message contains "exited Plan Mode" with a plan file path:
  PLAN_FILE_PATH = [path from system message]
  PLAN_CONTENT = Read(PLAN_FILE_PATH)

  Display: "Detected active plan from plan mode: {{basename of PLAN_FILE_PATH}}"

  CHANGE_DESCRIPTION = PLAN_CONTENT
```

### 2. Phase Resolution

#### Step 2.1: Discover all phases

```text
ALL_PHASES = {tools.list_all_phases}

IF count(ALL_PHASES) == 0:
  ERROR: "No phases found in project {{PLAN_NAME}}"
  SUGGEST: "Run respec-roadmap {{PLAN_NAME}} first to create phases"
  EXIT
```

#### Step 2.2: Single phase shortcut

```text
IF count(ALL_PHASES) == 1:
  PHASE_FILE_PATH = ALL_PHASES[0]
  Display: "Single phase found, auto-selected: {{basename}}"
  → Skip to Step 2.4
```

#### Step 2.3: Multi-phase relevance matching

```text
For each PHASE_FILE in ALL_PHASES:
  Read the Overview section (Objectives, Scope, Deliverables) — first 30 lines
  Assess relevance of CHANGE_DESCRIPTION to this phase's content

Rank phases by relevance to CHANGE_DESCRIPTION.

IF clear best match (one phase strongly relevant, others weak):
  PHASE_FILE_PATH = best match
  Display: "Auto-detected phase: {{name}}"
  Display: "Reason: [brief explanation of why this phase matches]"
  IF other phases have partial relevance:
    Display: "Note: This change may also touch concerns from: [other phase names]"
ELSE:
  Use AskUserQuestion:
    Question: "Which phase does this change belong to? '{{CHANGE_DESCRIPTION}}'"
    Header: "Select Phase for Patch"
    multiSelect: false
    Options: [ranked phases with objectives summary as description]

  PHASE_FILE_PATH = [selected from response]
```

#### Step 2.4: Extract canonical name and sync to MCP

```text
PHASE_NAME = [basename of PHASE_FILE_PATH without .md extension]

Display to user: "Located phase file: {{PHASE_NAME}}"

{tools.sync_phase_instructions}
```

**Important**:
- PLAN_NAME is used for all MCP storage operations
- PHASE_NAME is the canonical name extracted from file path
- All subsequent operations use PHASE_NAME (canonical)

### 3. Planning Loop (Amendment Task Creation)

Create a targeted amendment task through refinement:

#### Step 3.1: Initialize Planning Loop

```text
PLANNING_LOOP_ID = {tools.initialize_planning_loop}
```

#### Step 3.2: Link Planning Loop to Phase

```text
{tools.link_planning_loop}
```

#### Step 3.3: Invoke Patch Planner Agent

{tools.invoke_patch_planner}

Expected: Amendment task document stored in MCP and linked to loop

#### Step 3.4: Invoke Task Plan Critic Agent

{tools.invoke_task_plan_critic}

Expected: CriticFeedback stored in MCP planning loop

#### Step 3.5: MCP Planning Decision

```text
PLANNING_DECISION_RESPONSE = {tools.decide_planning_action}
PLANNING_DECISION = PLANNING_DECISION_RESPONSE.status
PLANNING_SCORE = PLANNING_DECISION_RESPONSE.current_score
PLANNING_ITERATION = PLANNING_DECISION_RESPONSE.iteration

Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

#### Step 3.6: Planning Decision Handling

```text
IF PLANNING_DECISION == "refine":
  Display: "⟳ Iteration {{PLANNING_ITERATION}} · Score: {{PLANNING_SCORE}}/100 — refining amendment task"
  Re-invoke patch-planner agent (same parameters).
  Re-invoke task-plan-critic agent (same parameters).
  Call MCP decision again.

ELIF PLANNING_DECISION == "complete":
  Display: "✅ Score: {{PLANNING_SCORE}}/100 — amendment task approved"
  Proceed to Step 4.

ELIF PLANNING_DECISION == "user_input":
  LATEST_FEEDBACK = {tools.get_feedback}

  Display LATEST_FEEDBACK to user with:
  - Current quality score and iteration
  - Key issues requiring attention

  Prompt user for guidance
  Store user feedback: {tools.store_user_feedback}
  Re-invoke patch-planner agent (same parameters)
  Re-invoke task-plan-critic agent (same parameters)
  Call MCP decision again
```

### 4. Mode Extraction + Reviewer Resolution

Parse amendment task to determine which specialist reviewers to activate:

#### Step 4.1: Retrieve Amendment Task

```text
TASK_MARKDOWN = {tools.get_task_document}
```

#### Step 4.2: Extract Step Modes

```text
STEP_MODES = set()

For each "#### Step N:" section in TASK_MARKDOWN:
  Scan Step content for mode indicators:
  IF contains frontend keywords (UI, component, template, CSS, accessibility, HTMX, React, Vue):
    STEP_MODES.add("frontend")
  IF contains API keywords (endpoint, REST, route, request, response, authentication, middleware):
    STEP_MODES.add("api")
  IF contains database keywords (schema, migration, model, query, index, SQL, ORM):
    STEP_MODES.add("database")
  IF contains infrastructure keywords (Docker, CI/CD, deployment, container, pipeline, environment):
    STEP_MODES.add("infrastructure")

Display: "Detected step modes: {{STEP_MODES}}"
```

#### Step 4.3: Resolve Active Reviewers

```text
ACTIVE_REVIEWERS = ["automated-quality-checker", "spec-alignment-reviewer"]

IF "frontend" in STEP_MODES:
  ACTIVE_REVIEWERS.append("frontend-reviewer")
IF "api" in STEP_MODES:
  ACTIVE_REVIEWERS.append("backend-api-reviewer")
IF "database" in STEP_MODES:
  ACTIVE_REVIEWERS.append("database-reviewer")
IF "infrastructure" in STEP_MODES:
  ACTIVE_REVIEWERS.append("infrastructure-reviewer")

Check for coding standards config files:
CONFIG_FILES = Glob(.respec-ai/config/*.md)
LANGUAGE_FILES = CONFIG_FILES excluding stack.md
IF LANGUAGE_FILES is not empty:
  ACTIVE_REVIEWERS.append("coding-standards-reviewer")

Read config files for coder agent:
STACK_CONFIG = Read(.respec-ai/config/stack.md) if file exists, else ""
LANGUAGE_CONFIGS = For each file in LANGUAGE_FILES: Read(file) — concatenated content

ACTIVE_REVIEWERS.append("review-consolidator")

# Loop IDs in this command:
#   PLANNING_LOOP_ID  — planning loop (amendment task creation)
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
```

#### Step 5.2: CRITICAL - Dual Loop ID Management

You now have TWO active loop IDs - DO NOT confuse them:

**task_loop_id = {{PLANNING_LOOP_ID}}**
- Purpose: Retrieve amendment task document (created during planning loop)
- Used by: coder (to get implementation plan), reviewers (to verify against Task/Phase)
- Storage: Task document linked to this loop

**coding_loop_id = {{CODING_LOOP_ID}}**
- Purpose: Phase 1 functional feedback
- Used by: coder (feedback retrieval), review-consolidator (feedback storage)
- Storage: CriticFeedback for code quality

**STANDARDS_LOOP_ID** (initialized in Step 6.5.1)
- Purpose: Phase 2 standards feedback
- Used by: coder (standards-only mode), coding-standards-reviewer (phase2_mode)

Pass BOTH IDs to coding agents. Never swap them.

#### Step 5.3: Code Implementation Cycle

{tools.invoke_coder}

Expected: Code implementation committed, platform status updated

#### Step 5.4: Phase 1 Review Team Orchestration

Launch ALL Phase 1 review agents (except consolidator) in parallel. Core reviewers always run; optional specialists based on PHASE1_REVIEWERS from Step 4.3. The review-consolidator MUST run AFTER all other reviewers complete. coding-standards-reviewer is excluded from Phase 1 and runs in Phase 2 only.

**Core Reviewers (always active):**
{tools.invoke_quality_checker}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-quality-check

{tools.invoke_spec_alignment}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-spec-alignment

**Optional Specialist Reviewers (from PHASE1_REVIEWERS):**
For each REVIEWER in PHASE1_REVIEWERS where REVIEWER is not core and not consolidator:
  {tools.invoke_dynamic_reviewer_pattern}

  Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-{{REVIEWER_SLUG}}

**Consolidator (always last, runs over PHASE1_REVIEWERS):**
{tools.invoke_consolidator}

Expected: Single CriticFeedback with Overall Score stored in MCP coding loop

#### MCP Coding Decision
```text
CODING_DECISION_RESPONSE = {tools.decide_coding_action}
CODING_DECISION = CODING_DECISION_RESPONSE.status
CODING_SCORE = CODING_DECISION_RESPONSE.current_score
CODING_ITERATION = CODING_DECISION_RESPONSE.iteration

Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

### 6. Coding Decision Handling

═══════════════════════════════════════════════
MANDATORY DECISION PROTOCOL
═══════════════════════════════════════════════
The MCP decision is FINAL. Execute the matching branch IMMEDIATELY.

"refine"     → Execute refinement. Do NOT ask, confirm, or present options to the user.
"user_input" → ONLY status that involves the user. Present feedback and wait for response.
"complete"   → Proceed to next step. Do NOT ask for confirmation.

VIOLATION: Asking the user "Should I continue refining?" when status is "refine"
           is a workflow violation. The decision has already been made by the MCP server.
═══════════════════════════════════════════════

```text
IF CODING_DECISION == "refine":
  Display: "🔵 [Phase 1 · Iteration {{CODING_ITERATION}}] ⟳ Score: {{CODING_SCORE}}/100 — refining"
  Re-invoke coder agent (same parameters).
  Re-invoke review team (Step 5.4: quality-checker -> spec-alignment -> specialists -> consolidator).
  Call MCP decision again.

ELIF CODING_DECISION == "complete":
  Display: "🔵 [Phase 1 · Complete] ✅ Score: {{CODING_SCORE}}/100 — threshold reached"
  IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS: Proceed to Step 6.5
  ELSE: Proceed to Step 7

ELIF CODING_DECISION == "user_input":
  LATEST_FEEDBACK = {tools.get_feedback}

  Display LATEST_FEEDBACK to user with:
  - Current quality score and iteration
  - Key issues requiring attention
  - Recommended improvements

  Prompt user for guidance
  Store user feedback: {tools.store_user_feedback}
  Re-invoke coder agent (same parameters)
  Re-invoke review team (Step 5.4: quality-checker -> spec-alignment -> specialists -> consolidator)
  Call MCP decision again
```

### 6.5: Standards Finalization Phase

═══════════════════════════════════════════════
MANDATORY PHASE 2 ACTIVATION GATE
═══════════════════════════════════════════════
Run ONLY IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS
(language config files detected in Step 4.3).

IF no config files were found in .respec-ai/config/:
  Skip Phase 2 entirely. Proceed directly to Step 7.
  Display: "ℹ️ No coding standards configured — skipping Phase 2"

Phase 2 has ZERO built-in rules. Without config files, there is
nothing to assess. Do NOT apply general coding standards.
═══════════════════════════════════════════════

#### Step 6.5.1: Initialize Standards Loop

```text
STANDARDS_LOOP_ID = {tools.initialize_standards_loop}

PHASE1_SCORE = [final Overall Score from CODING_LOOP_ID CriticFeedback]
Display:
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  PHASE 1 COMPLETE  ·  Functional Quality Score: {{PHASE1_SCORE}}/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟣  PHASE 2 STARTING: Coding Standards
    Focus: naming · imports · type hints · docstrings
    Completes with a pre-commit hook validated commit.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

#### Step 6.5.2: Standards Review Cycle

```text
Loop:

  {tools.invoke_coder_standards}

  {tools.invoke_coding_standards_reviewer}

  (No review-consolidator in Phase 2 — coding-standards-reviewer stores CriticFeedback directly)

  STANDARDS_DECISION_RESPONSE = {tools.decide_standards_action}
  STANDARDS_DECISION = STANDARDS_DECISION_RESPONSE.status
  STANDARDS_SCORE = STANDARDS_DECISION_RESPONSE.current_score
  STANDARDS_ITERATION = STANDARDS_DECISION_RESPONSE.iteration

  IF STANDARDS_DECISION == "complete":
    Display: "🟣 [Phase 2 · Complete] ✅ Score: {{STANDARDS_SCORE}}/100 — standards threshold reached"
    exit loop

  IF STANDARDS_DECISION == "refine":
    Display: "🟣 [Phase 2 · Iteration {{STANDARDS_ITERATION}}] ⟳ Score: {{STANDARDS_SCORE}}/100 — refining standards"
    continue loop

  IF STANDARDS_DECISION == "user_input":
    STANDARDS_FEEDBACK = {tools.get_standards_feedback}
    Display stagnation info with: phase 1 score, phase 2 current score, iterations, key issues

    Use AskUserQuestion with options:
      1. Continue Phase 2 with more iterations
      2. Accept current state — finalize with --no-verify
      3. Finalize now with pre-commit hooks (may fail)

    Store user choice and branch accordingly:
    - Option 1: continue loop
    - Option 2: git commit --no-verify -m "fix: {{CHANGE_DESCRIPTION}} [coding standards — hooks bypassed]"
                EXIT Phase 2 loop
    - Option 3: proceed to Step 6.5.3
```

#### Step 6.5.3: Final Commit with Pre-commit Hooks

```text
Run (without --no-verify):
  git add -A
  git commit -m "fix: {{CHANGE_DESCRIPTION}} — coding standards applied"

IF commit succeeds:
  Display:
  "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅  PHASE 2 COMPLETE  ·  Coding Standards Applied
  ✅  Pre-commit hooks passed — implementation complete
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

IF commit fails (hooks rejected):
  Display hook output

  Use AskUserQuestion:
    "Pre-commit hooks failed. Options:"
    1. Finalize with --no-verify (address hooks separately)
    2. Fix failures manually, then re-run

  IF option 1:
    git commit --no-verify -m "fix: {{CHANGE_DESCRIPTION}} [pre-commit hooks bypassed]"
```

### 7. Update Phase Evolution Log

Record the amendment in the Phase document for traceability:

```text
PHASE_MARKDOWN = {tools.get_phase_document}

TASK_NAME = [Extract task name from amendment task document]

Append Evolution Log section (or update existing):

## Evolution Log

### {{CURRENT_DATE}}: {{CHANGE_DESCRIPTION_SUMMARY}}
- Amendment Task: {{PLAN_NAME}}/{{PHASE_NAME}}/{{TASK_NAME}}
- Code Quality Score: {{CODE_QUALITY_SCORE}}%
- Files Changed: {{FILE_LIST}}

Store updated Phase:
{tools.update_phase_document}
```

### 8. Store Amendment Task + Report

#### Store to Filesystem

```text
{tools.task_location_setup}

Write amendment task to: .respec-ai/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/{{TASK_NAME}}.md
```

#### Report Completion

```text
Present final summary:
"Implementation complete for amendment: {{CHANGE_DESCRIPTION}}

Planning:
- Quality Score: {{PLAN_QUALITY_SCORE}}%
- Iterations: {{PLANNING_ITERATION_COUNT}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}

Amendment artifacts:
- Task: {{TASK_NAME}} stored under {{PHASE_NAME}}
- Phase Evolution Log: Updated
- Code Review: Available via coding_loop_id={{CODING_LOOP_ID}}

Ready for deployment."
```

## Phase Name Normalization Rules

**IMPORTANT:** Phase names are automatically normalized to kebab-case:

**File System to MCP Normalization:**
- Convert to lowercase: `Phase-1` -> `phase-1`
- Replace spaces/underscores with hyphens: `phase 1` -> `phase-1`
- Remove special characters: `phase-1!` -> `phase-1`
- Collapse multiple hyphens: `phase--1` -> `phase-1`
- Strip leading/trailing hyphens: `-phase-1-` -> `phase-1`

**Critical:** The H1 header in phase markdown MUST match the normalized file name.

## Quality Gates

### Quality Assessment
- **Amendment Task Evaluation**: Assessed by task-plan-critic agent (reused from respec-task)
- **Code Quality Evaluation**: Assessed by review team (same as respec-code)
- **Loop Decisions**: Made by MCP Server based on configuration
- **Thresholds and Limits**: Managed by MCP Server

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No Phase found: [PHASE_NAME]"
Suggest: "respec-phase [PLAN_NAME] [PHASE_NAME] to create Phase"
Exit gracefully with guidance
```

#### Planning Loop Failures
```text
IF patch-planner fails:
  Report failure with context
  Suggest manual task creation
  Provide diagnostic information
```

#### Coding Loop Failures
```text
IF coder fails:
  Preserve git commits for rollback
  Report failure with TodoList state
  Provide diagnostic information
  Suggest manual intervention

IF review team fails:
  Run static analysis manually
  Report test results without quality score
  Continue with manual quality assessment
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Running planning, coding, and standards loops** sequentially
- **Coordinating agent invocations** without defining their behavior
- **Maintaining triple loop IDs** (planning_loop_id + coding_loop_id + standards_loop_id)
- **Separating Phase 1 (functional) from Phase 2 (standards)** reviews
- **Handling MCP Server responses** without evaluating quality scores
- **Updating Phase evolution log** for traceability
- **Storing amendment task** to filesystem for documentation

All specialized work delegated to appropriate agents:
- **patch-planner**: Codebase exploration and amendment task creation
- **task-plan-critic**: Amendment task quality evaluation (reused)
- **coder**: TDD code implementation (reused)
- **review team**: Code quality evaluation (reused)
- **MCP Server**: Decision logic, threshold management, state storage
"""
