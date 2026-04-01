from src.platform.models import CodeCommandTools


def generate_code_command_template(tools: CodeCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase-name]
description: Transform Phases into production-ready code through TDD-driven implementation
---

# /respec-code Command: Implementation Orchestration

## Overview
Orchestrate the complete implementation workflow, transforming Phases into production-ready code through TDD-driven code development with comprehensive quality validation.

{tools.mcp_tools_reference}

## Workflow Steps

### 1. Extract Command Arguments and Locate Phase File

Parse command arguments and locate phase file using partial name:

#### Step 1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the project name]
PHASE_NAME_PARTIAL = [second argument from command - partial phase name]
```

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
  Use AskUserQuestion tool to present options:
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

  PHASE_FILE_PATH = [selected file path from AskUserQuestion response]
```

#### Step 1.4: Extract canonical name from file path

```text
PHASE_NAME = [basename of PHASE_FILE_PATH without .md extension]

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

### 5. Retrieve Task from /respec-task Command

Retrieve completed Task document from task workflow:

```text
TASK_MARKDOWN = {tools.get_task_document}

IF TASK_MARKDOWN not found:
  ERROR: "No Task found for Phase: {{PHASE_NAME}}"
  SUGGEST: "Run '/respec-task {{PLAN_NAME}} {{PHASE_NAME}}' to create Task first"
  EXIT: Graceful failure with guidance

Display: "✓ Task retrieved - ready for implementation"
```

### 6. Check for Architectural Override Proposals

Use Task already retrieved in Step 5:

```text
# REUSE TASK_MARKDOWN from Step 5 (do not re-retrieve)

IF TASK_MARKDOWN contains "## Architectural Override Proposals" section:
  OVERRIDE_SECTION = [Extract section content]

  IF OVERRIDE_SECTION is not empty (has content beyond just header):
    Display to user:
    "⚠️ Task-planner has identified potential architecture improvements.

    Review override proposals in Task document.

    Choose action:
    1. Approve proposal → Re-run /respec-phase to update architecture
    2. Reject proposal → Continue with current Phase as-is

    Task workflow paused until Phase updated.

    To approve: /respec-phase {{PLAN_NAME}} {{PHASE_NAME}} [instructions based on proposal]
    To reject: Re-run /respec-code {{PLAN_NAME}} {{PHASE_NAME}}"

    EXIT: Workflow suspended pending user decision

Proceed to Step 6.5 (Mode Extraction)
```

### 6.5 Extract Step Modes from Task

Parse Task document to determine which specialist reviewers to activate:

```text
# REUSE TASK_MARKDOWN from Step 5 (do not re-retrieve)

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
#   PLANNING_LOOP_ID  — task breakdown loop (from /respec-task)
#   CODING_LOOP_ID    — Phase 1 functional loop (AQC + spec-alignment + domains)
#   STANDARDS_LOOP_ID — Phase 2 standards loop (coding-standards-reviewer only)
# Coder receives the loop ID matching its current phase.
# Each agent retrieves its own feedback using the loop_id it was given.

PHASE1_REVIEWERS = ACTIVE_REVIEWERS excluding "coding-standards-reviewer"
(coding-standards-reviewer runs in Phase 2 only)

Display: "✓ Active reviewers: {{ACTIVE_REVIEWERS}}"
Display: "✓ Phase 1 reviewers: {{PHASE1_REVIEWERS}}"
```

### 7. Coding Loop Initialization and Refinement
Set up and execute MCP-managed code quality refinement:

#### Step 7.1: Retrieve Task Loop ID from Task Workflow

Retrieve the task_loop_id that was created during /respec-task:

```text
TASK_INFO = {tools.get_task_document}

TASK_LOOP_ID = [Extract loop_id from task metadata or use plan_name/phase_name to find active task loop]
```

#### Step 7.2: Initialize Coding Loop
```text
CODING_LOOP_ID = {tools.initialize_coding_loop}
```

#### Step 7.3: CRITICAL - Dual Loop ID Management

You now have TWO active loop IDs - DO NOT confuse them:

**task_loop_id = {{TASK_LOOP_ID}}**
- Purpose: Retrieve Task document (created during /respec-task)
- Used by: coder (to get implementation plan), reviewers (to verify against Task/Phase)
- Storage: Task document linked to this loop

**coding_loop_id = {{CODING_LOOP_ID}}**
- Purpose: Store/retrieve code feedback
- Used by: coder (feedback retrieval), review-consolidator (feedback storage)
- Storage: CriticFeedback for code quality

Pass BOTH IDs to coding agents. Never swap them.

#### Step 7.4: Code Implementation Cycle
{tools.invoke_coder}

Expected: Code implementation committed, platform status updated

#### Step 7.4.1: Review Team Orchestration

Launch ALL Phase 1 review agents (except consolidator) in parallel. Core reviewers always run; optional specialists based on PHASE1_REVIEWERS from Step 6.6. The review-consolidator MUST run AFTER all other reviewers complete. coding-standards-reviewer is excluded from Phase 1 and runs in Phase 2 only.

**Core Reviewers (always active):**
{tools.invoke_quality_checker}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-quality-check

{tools.invoke_spec_alignment}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-spec-alignment

{tools.invoke_code_quality}

Expected: Review section stored at {{PLAN_NAME}}/{{PHASE_NAME}}/review-code-quality

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

### 8. Coding Decision Handling

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
  Display: "🔵 [Phase 1 · Iteration {{CODING_ITERATION}}] ⟳ Score: {{CODING_SCORE}}/100 — refining"
  Re-invoke coder agent (same parameters).
  Re-invoke review team (Step 7.4.1: quality-checker → spec-alignment → specialists → consolidator).
  Call MCP decision again.

ELIF CODING_DECISION == "complete":
  Display: "🔵 [Phase 1 · Complete] ✅ Score: {{CODING_SCORE}}/100 — threshold reached"
  IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
    → IMMEDIATELY execute Step 7.5 (Standards Finalization Phase)
  ELSE:
    → IMMEDIATELY execute Step 9 (Integration & Documentation)
  DO NOT ask user, DO NOT offer alternatives, DO NOT pause

ELIF CODING_DECISION == "user_input":
  LATEST_FEEDBACK = {tools.get_feedback}

  Display LATEST_FEEDBACK to user with:
  - Current quality score and iteration
  - Key issues requiring attention
  - Recommended improvements

  Prompt user for guidance
  Store user feedback: {tools.store_user_feedback}
  Re-invoke coder agent (same parameters)
  Re-invoke review team (Step 7.4.1: quality-checker → spec-alignment → specialists → consolidator)
  Call MCP decision again
```

### 7.5: Standards Finalization Phase

Run ONLY IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS (language config files detected in Step 6.6).

#### Step 7.5.1: Initialize Standards Loop

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

#### Step 7.5.2: Standards Review Cycle

```text
Loop:

  {tools.invoke_coder_standards}

  {tools.invoke_coding_standards_reviewer}

  (No review-consolidator in Phase 2 — coding-standards-reviewer stores CriticFeedback directly)

  STANDARDS_DECISION_RESPONSE = {tools.decide_standards_action}
  STANDARDS_DECISION = STANDARDS_DECISION_RESPONSE.status
  STANDARDS_SCORE = STANDARDS_DECISION_RESPONSE.current_score
  STANDARDS_ITERATION = STANDARDS_DECISION_RESPONSE.iteration

  ═══════════════════════════════════════════════
  MANDATORY STANDARDS LOOP LIMIT
  ═══════════════════════════════════════════════
  Maximum standards loop iterations: 5

  IF STANDARDS_ITERATION >= 5 AND STANDARDS_DECISION == "refine":
    Force "user_input" path — present feedback and wait for user guidance
    Display: "⚠ Standards loop reached iteration limit (5)"
  ═══════════════════════════════════════════════

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
    - Option 2: git commit --no-verify -m "feat: implement {{PHASE_NAME}} [coding standards — hooks bypassed]"
                EXIT Phase 2 loop
    - Option 3: proceed to Step 7.5.3
```

#### Step 7.5.3: Final Commit with Pre-commit Hooks

```text
Run (without --no-verify):
  git add -A
  git commit -m "feat: implement {{PHASE_NAME}} — coding standards applied"

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
    git commit --no-verify -m "feat: implement {{PHASE_NAME}} [pre-commit hooks bypassed]"
```

### 9. Integration & Documentation
Complete implementation workflow and update Phase:

#### Generate Implementation Summary
```text
Retrieve final state:
- Phase: {tools.get_task_document})
- Final Feedback: {tools.get_feedback})

Generate IMPLEMENTATION_SUMMARY including:
- Task Plan Quality Score: {{PLAN_QUALITY_SCORE}}%
- Code Quality Score: {{CODE_QUALITY_SCORE}}%
- Test Results: {{TEST_RESULTS from CriticFeedback}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Files Modified: {{FILE_COUNT}}
- Commit Summary: {{GIT_LOG_SUMMARY}}
```

#### Update Phase
```text
Update Phase status and implementation details using {tools.store_phase_document}:

Status: "IMPLEMENTED"
Implementation Summary: {{IMPLEMENTATION_SUMMARY}}
Phase Quality: {{PLAN_QUALITY_SCORE}}%
Code Quality: {{CODE_QUALITY_SCORE}}%
Test Coverage: {{COVERAGE_PERCENTAGE}}%
Implementation Date: {{CURRENT_DATE}}
```

#### Report Completion
```text
Present final summary:
"✓ Implementation complete for {{PHASE_NAME}}

Task Planning:
- Quality Score: {{PLAN_QUALITY_SCORE}}%
- Iterations: {{TASK_ITERATION_COUNT}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Type Checker: {{TYPE_CHECKER_STATUS}}
- Linter: {{LINTER_STATUS}}

Implementation artifacts:
- Phase: Available via task_loop_id={{TASK_LOOP_ID}}
- Code Review: Available via coding_loop_id={{CODING_LOOP_ID}}
- Commits: {{COMMIT_COUNT}} commits with test results
- Phase Status: Updated via {tools.store_phase_document}

Ready for deployment."
```

## Phase Name Normalization Rules

**IMPORTANT:** Phase names are automatically normalized to kebab-case:

**File System → MCP Normalization:**
- Convert to lowercase: `Phase-1` → `phase-1`
- Replace spaces/underscores with hyphens: `phase 1` → `phase-1`
- Remove special characters: `phase-1!` → `phase-1`
- Collapse multiple hyphens: `phase--1` → `phase-1`
- Strip leading/trailing hyphens: `-phase-1-` → `phase-1`

**Critical:** The H1 header in phase markdown MUST match the normalized file name:
- File: `phase-2a-neo4j-schema-and-llama-index-integration.md`
- H1 header: `# Phase: phase-2a-neo4j-schema-and-llama-index-integration`
- Mismatch will cause storage/retrieval failures

**Build agents:** Use normalized phase names when retrieving Phases via MCP.

## Quality Gates

### Quality Assessment
- **Phase Evaluation**: Assessed by task-critic agent
- **Code Quality Evaluation**: Assessed by review team (automated-quality-checker, spec-alignment-reviewer, code-quality-reviewer, optional specialists, review-consolidator)
- **Loop Decisions**: Made by MCP Server based on configuration
- **Thresholds and Limits**: Managed by MCP Server

### Assessment Criteria

**Phase Assessment Criteria**:
1. Plan Completeness: All sections populated with substantive content
2. Phase Alignment: Matches objectives, scope, architecture
3. Test Strategy Clarity: TDD approach and test organization defined
4. Implementation Sequence Logic: Dependencies respected, phases logical
5. Technology Appropriateness: Stack suitable for requirements

**Code Quality Assessment Criteria**:
1. Tests Passing: All tests execute successfully
2. Type Checking Clean: Type checker reports zero errors
3. Linting Clean: Linter reports zero issues
4. Test Coverage: Adequate coverage of critical paths
5. Phase Alignment: File structure and features match plan
6. Phase Requirements: All objectives implemented

Note: Loop decisions determined by MCP Server based on scoring and configuration

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No Phase found: [PHASE_NAME]"
Suggest: "/respec-phase [PLAN_NAME] [PHASE_NAME] to create Phase"
Exit gracefully with guidance
```

#### Coding Loop Failures
```text
IF coder fails:
  Preserve git commits for rollback
  Report failure with TodoList state
  Provide diagnostic information
  Suggest manual intervention

IF review team fails:
  Run static analysis manually (Bash: test runner, type checker, linter from Phase tech stack)
  Report test results without quality score
  Continue with manual quality assessment
  Note automated review unavailable
```

#### MCP Loop Failures
```text
IF loop initialization fails:
  Continue with single-pass workflow
  Skip refinement cycles
  Note quality loops unavailable
  Suggest manual review at each phase
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Validating Phase completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Maintaining dual loop IDs** (task_loop_id + coding_loop_id)
- **Handling MCP Server responses** without evaluating quality scores
- **Managing user feedback** during stagnation scenarios
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **coder**: TDD code implementation (MCP access + platform tools)
- **automated-quality-checker**: Static analysis (tests, types, lint, coverage)
- **spec-alignment-reviewer**: Task/Phase/Plan alignment verification
- **code-quality-reviewer**: Structural quality, correctness patterns, research compliance, design assessment
- **specialist reviewers**: Domain-specific review (frontend, API, database, infrastructure)
- **review-consolidator**: Merges all review sections into single CriticFeedback
- **MCP Server**: Decision logic, threshold management, state storage

## Workflow Enhancements

### Dual Loop Architecture
- Separate task loop (from /respec-task) and coding loop (code refinement)
- task_loop_id used to retrieve Task document created by task workflow
- coding_loop_id used for code feedback storage/retrieval
- Coding agents receive both IDs and use appropriately

### Coding Standards Integration
- coder reads platform-specific coding standards on initialization
- User-customizable coding standards applied to all generated code
- Fallback to Phase Code Standards if not available

### TDD Enforcement
- Strict test-first discipline enforced by coder agent
- Tests must fail before implementation proceeds
- Tests must pass before considering feature complete
- Commit after each iteration for rollback capability

### User Feedback During Stagnation
- User input requested when quality plateaus (<5 points over 2 iterations)
- User feedback stored via {tools.store_user_feedback}
- Agents retrieve all feedback (critic + user) via {tools.get_feedback}
- User feedback takes priority over critic suggestions when conflicts exist

Ready for production deployment with validated quality scores and comprehensive test coverage.
"""
