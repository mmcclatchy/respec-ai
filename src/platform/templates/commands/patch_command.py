from src.platform.models import PatchCommandTools


def generate_patch_command_template(tools: PatchCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [change-description]
description: Update existing code through amendment tasks with full quality review
---

# /respec-patch Command: Maintenance Orchestration

## Overview
Orchestrate bug fixes, feature extensions, and refactoring of existing code through amendment tasks with the same quality scoring, review loops, and documentation trail as /respec-code.

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
   "from plan mode", or contains a path to a .md file in ~/.claude/plans/):

  PLAN_FILE_PATH = [extract or infer path from CHANGE_DESCRIPTION]
  IF PLAN_FILE_PATH not explicitly provided:
    PLAN_FILE_PATH = Glob(~/.claude/plans/*.md) → select most recently modified

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
  SUGGEST: "Run /respec-roadmap {{PLAN_NAME}} first to create phases"
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

```text
Invoke patch-planner agent with:
- task_loop_id: {{PLANNING_LOOP_ID}}
- plan_name: {{PLAN_NAME}}
- phase_name: {{PHASE_NAME}}
- change_description: {{CHANGE_DESCRIPTION}}

Expected: Amendment task document stored in MCP and linked to loop
```

#### Step 3.4: Invoke Task Plan Critic Agent

```text
Invoke task-plan-critic agent with:
- task_loop_id: {{PLANNING_LOOP_ID}}
- plan_name: {{PLAN_NAME}}
- phase_name: {{PHASE_NAME}}

Expected: CriticFeedback stored in MCP planning loop
```

#### Step 3.5: MCP Planning Decision

```text
PLANNING_DECISION_RESPONSE = {tools.decide_planning_action}
PLANNING_DECISION = PLANNING_DECISION_RESPONSE.status

Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

#### Step 3.6: Planning Decision Handling

```text
IF PLANNING_DECISION == "refine":
  Re-invoke patch-planner agent (same parameters).
  Re-invoke task-plan-critic agent (same parameters).
  Call MCP decision again.

ELIF PLANNING_DECISION == "complete":
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

Check for coding standards file:
IF coding standards file exists at project root (CLAUDE.md with coding standards content):
  ACTIVE_REVIEWERS.append("coding-standards-reviewer")

ACTIVE_REVIEWERS.append("review-consolidator")

Display: "Active reviewers: {{ACTIVE_REVIEWERS}}"
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
- Purpose: Store/retrieve code feedback
- Used by: coder (feedback retrieval), review-consolidator (feedback storage)
- Storage: CriticFeedback for code quality

Pass BOTH IDs to coding agents. Never swap them.

#### Step 5.3: Code Implementation Cycle

```text
Invoke coder agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- task_loop_id: {{PLANNING_LOOP_ID}} (CRITICAL - for Task retrieval)
- plan_name: {{PLAN_NAME}}
- phase_name: {{PHASE_NAME}}

Expected: Code implementation committed, platform status updated
```

#### Step 5.4: Review Team Orchestration

Invoke review agents sequentially. Core reviewers always run; optional specialists based on ACTIVE_REVIEWERS from Step 4.3.

**Core Reviewers (always active):**
```text
Invoke automated-quality-checker agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- task_loop_id: {{PLANNING_LOOP_ID}}
- plan_name: {{PLAN_NAME}}
- phase_name: {{PHASE_NAME}}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-quality-check
```

```text
Invoke spec-alignment-reviewer agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- task_loop_id: {{PLANNING_LOOP_ID}}
- plan_name: {{PLAN_NAME}}
- phase_name: {{PHASE_NAME}}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-spec-alignment
```

**Optional Specialist Reviewers (from ACTIVE_REVIEWERS):**
```text
For each REVIEWER in ACTIVE_REVIEWERS where REVIEWER is not core and not consolidator:
  Invoke {{REVIEWER}} agent with:
  - coding_loop_id: {{CODING_LOOP_ID}}
  - task_loop_id: {{PLANNING_LOOP_ID}}
  - plan_name: {{PLAN_NAME}}
  - phase_name: {{PHASE_NAME}}

  Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-{{REVIEWER_SLUG}}
```

**Consolidator (always last):**
```text
Invoke review-consolidator agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- plan_name: {{PLAN_NAME}}
- phase_name: {{PHASE_NAME}}
- active_reviewers: {{ACTIVE_REVIEWERS}}

Expected: Single CriticFeedback with Overall Score stored in MCP coding loop
```

#### MCP Coding Decision
```text
CODING_DECISION_RESPONSE = {tools.decide_coding_action}
CODING_DECISION = CODING_DECISION_RESPONSE.status

Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

### 6. Coding Decision Handling

**Follow CODING_DECISION exactly. Do not override based on score assessment.**

```text
IF CODING_DECISION == "refine":
  Re-invoke coder agent (same parameters).
  Re-invoke review team (Step 5.4: quality-checker -> spec-alignment -> specialists -> consolidator).
  Call MCP decision again.

ELIF CODING_DECISION == "complete":
  Proceed to Step 7.

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
- **Amendment Task Evaluation**: Assessed by task-plan-critic agent (reused from /respec-task)
- **Code Quality Evaluation**: Assessed by review team (same as /respec-code)
- **Loop Decisions**: Made by MCP Server based on configuration
- **Thresholds and Limits**: Managed by MCP Server

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No Phase found: [PHASE_NAME]"
Suggest: "/respec-phase [PLAN_NAME] [PHASE_NAME] to create Phase"
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
- **Running BOTH planning and coding loops** sequentially
- **Coordinating agent invocations** without defining their behavior
- **Maintaining dual loop IDs** (planning_loop_id + coding_loop_id)
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
