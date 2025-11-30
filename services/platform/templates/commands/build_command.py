from services.platform.models import BuildCommandTools


def generate_build_command_template(tools: BuildCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [spec-name]
description: Transform technical specifications into production-ready code through parallel research, implementation planning, and TDD development
---

# /specter-build Command: Implementation Orchestration

## Overview
Orchestrate the complete implementation workflow, transforming technical specifications into production-ready code through parallel research synthesis, implementation planning, and TDD-driven code development with comprehensive quality validation.

## Workflow Steps

### 0. Initialize Project Context

Read project configuration:
```text
Read .specter/config.json
PROJECT_NAME = config["project_name"]
```

**Important**: PROJECT_NAME from config is used for all MCP storage operations.

### 0a. Load Existing Spec from Platform

Load existing spec from platform (if exists):

```text
# Get spec name from user argument
SPEC_NAME = [user provided spec name]

{tools.sync_spec_instructions}
```

**Note**: Build plans are not stored in external platforms - they only exist in MCP during the build workflow.

### 1. Specification Retrieval and Validation
Retrieve and validate completed TechnicalSpec from /specter-spec command:

#### Retrieve TechnicalSpec
```text
SPEC_NAME = [user provided spec name]

TECHNICAL_SPEC = mcp__specter__get_spec_markdown(PROJECT_NAME, SPEC_NAME)
IF TECHNICAL_SPEC not found:
  ERROR: "No technical specification found: [SPEC_NAME]"
  SUGGEST: "Run '/specter-spec [SPEC_NAME]' to create technical specification first"
  EXIT: Graceful failure with guidance

SPEC_OBJECTIVES = [Extract from TechnicalSpec Objectives section]
RESEARCH_REQUIREMENTS = [Extract from TechnicalSpec Research Requirements section]
TECH_STACK = [Extract from TechnicalSpec Technology Stack section]
```

### 2. Parallel Research Orchestration
Coordinate research synthesis for implementation guidance:

#### Parse Research Requirements
```text
DOCUMENTATION_PATHS = []

For each item in RESEARCH_REQUIREMENTS:

  IF item starts with "Read:":
    EXISTING_PATH = [Extract path from "Read: [path]"]
    Add EXISTING_PATH to DOCUMENTATION_PATHS

  IF item starts with "Synthesize:":
    RESEARCH_PROMPT = [Extract prompt from "Synthesize: [prompt]"]

    Launch parallel research-synthesizer agents (single message, multiple Task calls):
    Task(
        agent="research-synthesizer",
        prompt=RESEARCH_PROMPT
    )

    Expected: Research brief file path from each agent
    SYNTHESIZED_PATH = [research-synthesizer output: document path]
    Add SYNTHESIZED_PATH to DOCUMENTATION_PATHS

Collect: COMPLETE_DOCUMENTATION_PATHS = [All paths from existing docs + research synthesis]
```

### 3. Planning Loop Initialization and Refinement
Set up and execute MCP-managed planning quality refinement:

#### Initialize Planning Loop
```text
PLANNING_LOOP_ID = mcp__specter__initialize_refinement_loop(loop_type='build_plan')

State to maintain:
- planning_loop_id: For BuildPlan storage and retrieval
```

#### Planning Refinement Cycle
```text
Invoke build-planner agent with:
- planning_loop_id: {{PLANNING_LOOP_ID}}
- research_file_paths: {{COMPLETE_DOCUMENTATION_PATHS}}
- project_name: {{PROJECT_NAME}}
- spec_name: {{SPEC_NAME}}

Agent will autonomously:
1. Read .specter/coding-standards.md (if exists)
2. Retrieve TechnicalSpec via MCP
3. Retrieve existing BuildPlan via MCP (empty on first iteration)
4. Retrieve critic feedback via MCP (none on first iteration)
5. Retrieve user feedback via MCP (if stagnation occurred)
6. Read research briefs from file paths
7. Generate or refine BuildPlan
8. Store BuildPlan via MCP
9. Exit

Expected: BuildPlan stored in MCP with planning_loop_id
```

#### Planning Quality Assessment
```text
Invoke build-critic agent with:
- planning_loop_id: {{PLANNING_LOOP_ID}}
- project_name: {{PROJECT_NAME}}
- spec_name: {{SPEC_NAME}}

Agent will autonomously:
1. Retrieve BuildPlan via MCP
2. Retrieve TechnicalSpec via MCP
3. Retrieve previous critic feedback via MCP (for progress tracking)
4. Assess BuildPlan against FSDD criteria (5 categories, 100 points total)
5. Calculate quality score (0-100)
6. Generate CriticFeedback markdown
7. Store CriticFeedback via MCP
8. Exit

Expected: CriticFeedback with Overall Score stored in MCP
```

#### MCP Planning Decision
```text
PLANNING_DECISION = mcp__specter__decide_loop_next_action(
    loop_id=PLANNING_LOOP_ID,
    current_score=PLAN_QUALITY_SCORE
)

Returns:
- "refine" if score < 80%
- "complete" if score >= 80%
- "user_input" if stagnation detected (<5 points improvement over 2 iterations)
```

### 4. Planning Decision Handling
Handle MCP Server planning phase responses:

#### If PLANNING_DECISION == "refine"
```text
Re-invoke build-planner agent (same parameters)
Agent retrieves previous critic feedback and incorporates into refinement
Re-invoke build-critic agent
Call MCP decision again
Continue until "complete" or "user_input"
```

#### If PLANNING_DECISION == "complete"
```text
Proceed to Step 5: Coding Loop Initialization
```

#### If PLANNING_DECISION == "user_input"
```text
Stagnation detected in planning loop. Request user guidance:

Retrieve current state:
- BuildPlan: mcp__specter__get_build_plan_markdown(PLANNING_LOOP_ID)
- All Feedback: mcp__specter__get_feedback(PLANNING_LOOP_ID, count=2)

Present to user:
"BuildPlan development has stagnated at {{PLAN_QUALITY_SCORE}}%.

Key Issues:
{{CriticFeedback Key Issues section}}

Recommendations:
{{CriticFeedback Recommendations section}}

Please provide guidance on:
1. Specific technical approach preferences
2. Alternative implementation strategies
3. Accept current plan and proceed to coding: yes/no"

Collect user response as USER_FEEDBACK_MARKDOWN

Store user feedback:
mcp__specter__store_user_feedback(PLANNING_LOOP_ID, USER_FEEDBACK_MARKDOWN)

Re-invoke build-planner (will retrieve user feedback autonomously)
Continue refinement with user guidance
```

### 5. Coding Loop Initialization and Refinement
Set up and execute MCP-managed code quality refinement:

#### Initialize Coding Loop
```text
CODING_LOOP_ID = mcp__specter__initialize_refinement_loop(loop_type='build_code')

State to maintain (CRITICAL - TWO loop IDs):
- planning_loop_id: For retrieving BuildPlan
- coding_loop_id: For code feedback storage/retrieval
```

#### Code Implementation Cycle
```text
Invoke build-coder agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- planning_loop_id: {{PLANNING_LOOP_ID}} (CRITICAL - for BuildPlan retrieval)
- project_name: {{PROJECT_NAME}}
- spec_name: {{SPEC_NAME}}

Agent will autonomously:
1. Read .specter/coding-standards.md (if exists, otherwise use BuildPlan Code Standards)
2. Retrieve BuildPlan via MCP using planning_loop_id
3. Retrieve TechnicalSpec via MCP
4. Retrieve critic feedback via MCP using coding_loop_id (none on first iteration)
5. Retrieve user feedback via MCP using coding_loop_id (if stagnation occurred)
6. Inspect codebase (Read/Glob to check current state)
7. Create TodoList (TodoWrite)
8. Execute TDD cycle:
   - Write test (Write/Edit)
   - Run test, verify fails (Bash: pytest)
   - Implement code (Write/Edit)
   - Run test, verify passes (Bash: pytest)
   - Run full suite (Bash: pytest --cov)
   - Run static analysis (Bash: mypy, ruff)
9. Commit changes (Bash: git add, git commit with test results)
10. Update platform task status (using agent's platform-specific tool)
11. Exit

Expected: Code implementation committed, platform status updated
```

#### Code Quality Assessment
```text
Invoke build-reviewer agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- planning_loop_id: {{PLANNING_LOOP_ID}} (CRITICAL - for BuildPlan retrieval)
- project_name: {{PROJECT_NAME}}
- spec_name: {{SPEC_NAME}}

Agent will autonomously:
1. Retrieve BuildPlan via MCP using planning_loop_id
2. Retrieve TechnicalSpec via MCP
3. Retrieve previous critic feedback via MCP using coding_loop_id (for progress tracking)
4. Inspect codebase (Read/Glob)
5. Run static analysis (Bash: mypy, ruff)
6. Run test suite (Bash: pytest --cov)
7. Assess code quality against criteria (6 categories, 100 points total)
8. Calculate quality score (0-100)
9. Generate CriticFeedback markdown with test results
10. Store CriticFeedback via MCP using coding_loop_id
11. Exit

Expected: CriticFeedback with Overall Score and test results stored in MCP
```

#### MCP Coding Decision
```text
CODING_DECISION = mcp__specter__decide_loop_next_action(
    loop_id=CODING_LOOP_ID,
    current_score=CODE_QUALITY_SCORE
)

Returns:
- "refine" if score < 95%
- "complete" if score >= 95%
- "user_input" if stagnation detected (<5 points improvement over 2 iterations)
```

### 6. Coding Decision Handling
Handle MCP Server coding phase responses:

#### If CODING_DECISION == "refine"
```text
Re-invoke build-coder agent (same parameters)
Agent retrieves previous critic feedback and user feedback (if any)
Agent addresses feedback items and continues implementation
Re-invoke build-reviewer agent
Call MCP decision again
Continue until "complete" or "user_input"
```

#### If CODING_DECISION == "complete"
```text
Proceed to Step 7: Integration & Documentation
```

#### If CODING_DECISION == "user_input"
```text
Stagnation detected in coding loop. Request user guidance:

Retrieve current state:
- BuildPlan: mcp__specter__get_build_plan_markdown(PLANNING_LOOP_ID)
- All Feedback: mcp__specter__get_feedback(CODING_LOOP_ID, count=2)

Present to user:
"Code implementation has stagnated at {{CODE_QUALITY_SCORE}}%.

Test Results:
{{CriticFeedback Test Execution Results section}}

Key Issues:
{{CriticFeedback Key Issues section}}

Recommendations:
{{CriticFeedback Recommendations section}}

Please provide guidance on:
1. Specific code quality concerns or trade-offs
2. Alternative implementation approaches
3. Accept current quality and complete: yes/no
4. Technical constraints or requirements adjustment"

Collect user response as USER_FEEDBACK_MARKDOWN

Store user feedback:
mcp__specter__store_user_feedback(CODING_LOOP_ID, USER_FEEDBACK_MARKDOWN)

Re-invoke build-coder (will retrieve user feedback autonomously)
Continue refinement with user guidance
```

### 7. Integration & Documentation
Complete implementation workflow and update specification:

#### Generate Implementation Summary
```text
Retrieve final state:
- BuildPlan: mcp__specter__get_build_plan_markdown(PLANNING_LOOP_ID)
- Final Feedback: mcp__specter__get_feedback(CODING_LOOP_ID, count=1)

Generate IMPLEMENTATION_SUMMARY including:
- Build Plan Quality Score: {{PLAN_QUALITY_SCORE}}%
- Code Quality Score: {{CODE_QUALITY_SCORE}}%
- Test Results: {{TEST_RESULTS from CriticFeedback}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Files Modified: {{FILE_COUNT}}
- Commit Summary: {{GIT_LOG_SUMMARY}}
```

#### Update TechnicalSpec
```text
Update specification status and implementation details using mcp__specter__store_spec:

Status: "IMPLEMENTED"
Implementation Summary: {{IMPLEMENTATION_SUMMARY}}
BuildPlan Quality: {{PLAN_QUALITY_SCORE}}%
Code Quality: {{CODE_QUALITY_SCORE}}%
Test Coverage: {{COVERAGE_PERCENTAGE}}%
Implementation Date: {{CURRENT_DATE}}
```

#### Report Completion
```text
Present final summary:
"✓ Implementation complete for {{SPEC_NAME}}

Build Planning:
- Quality Score: {{PLAN_QUALITY_SCORE}}%
- Iterations: {{PLANNING_ITERATION_COUNT}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- MyPy: {{MYPY_STATUS}}
- Ruff: {{RUFF_STATUS}}

Implementation artifacts:
- BuildPlan: Available via planning_loop_id={{PLANNING_LOOP_ID}}
- Code Review: Available via coding_loop_id={{CODING_LOOP_ID}}
- Commits: {{COMMIT_COUNT}} commits with test results
- Spec Status: Updated via mcp__specter__store_spec

Ready for deployment."
```

## Quality Gates

### Planning Quality Threshold
- **Target Score**: 80/100 points minimum
- **Maximum Iterations**: 5 (configurable via FSDD_LOOP_BUILD_PLAN_MAX_ITERATIONS)
- **Stagnation Detection**: <5 points improvement over 2 iterations triggers user_input

### Code Quality Threshold
- **Target Score**: 95/100 points minimum
- **Maximum Iterations**: 5 (configurable via FSDD_LOOP_BUILD_CODE_MAX_ITERATIONS)
- **Stagnation Detection**: <5 points improvement over 2 iterations triggers user_input

### Assessment Criteria

**BuildPlan Assessment (80% threshold)**:
1. Plan Completeness (20 points): All sections populated
2. TechnicalSpec Alignment (25 points): Matches objectives, scope, architecture
3. Test Strategy Clarity (20 points): TDD approach defined
4. Implementation Sequence Logic (20 points): Dependencies respected
5. Technology Appropriateness (15 points): Stack suitable for requirements

**Code Assessment (95% threshold)**:
1. Tests Passing (30 points): All tests pass
2. Type Checking Clean (15 points): MyPy zero errors
3. Linting Clean (10 points): Ruff zero issues
4. Test Coverage (15 points): ≥80% coverage
5. BuildPlan Alignment (15 points): File structure and features match
6. TechnicalSpec Requirements (15 points): All objectives implemented

## Error Handling

### Graceful Degradation Patterns

#### TechnicalSpec Not Available
```text
Display: "No technical specification found: [spec-name]"
Suggest: "/specter-spec [spec-name] to create technical specification"
Exit gracefully with guidance
```

#### Research Synthesis Failures
```text
IF some research-synthesizer agents fail:
  Continue with available documentation
  Note missing research areas in DOCUMENTATION_PATHS
  Flag gaps in BuildPlan for user awareness
  Proceed with available research
```

#### Planning Loop Failures
```text
IF build-planner fails:
  Retry once with simplified context
  Create minimal BuildPlan from TechnicalSpec
  Note limitations and suggest manual review

IF build-critic fails:
  Continue without quality assessment
  Use single-pass BuildPlan
  Warn user that quality not validated
  Suggest manual review before coding
```

#### Coding Loop Failures
```text
IF build-coder fails:
  Preserve git commits for rollback
  Report failure with TodoList state
  Provide diagnostic information
  Suggest manual intervention

IF build-reviewer fails:
  Run static analysis manually (Bash: pytest, mypy, ruff)
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
- **Validating TechnicalSpec completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Maintaining dual loop IDs** (planning_loop_id + coding_loop_id)
- **Handling MCP Server responses** without evaluating quality scores
- **Managing user feedback** during stagnation scenarios
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **build-planner**: BuildPlan generation with research integration (MCP access)
- **build-critic**: BuildPlan quality assessment (80% threshold)
- **build-coder**: TDD code implementation with platform integration (MCP access + platform tools)
- **build-reviewer**: Code quality assessment (95% threshold)
- **research-synthesizer**: Parallel research brief generation
- **MCP Server**: Decision logic, threshold management, state storage

## Workflow Enhancements

### Dual Loop Architecture
- Separate planning loop (BuildPlan refinement) and coding loop (code refinement)
- planning_loop_id used for BuildPlan storage/retrieval by all agents
- coding_loop_id used for code feedback storage/retrieval
- Agents receive both IDs and use appropriately

### Coding Standards Integration
- build-coder reads .specter/coding-standards.md on initialization
- User-customizable coding standards applied to all generated code
- Fallback to BuildPlan Code Standards if file doesn't exist

### TDD Enforcement
- Strict test-first discipline enforced by build-coder agent
- Tests must fail before implementation proceeds
- Tests must pass before considering feature complete
- Commit after each iteration for rollback capability

### User Feedback During Stagnation
- User input requested when quality plateaus (<5 points over 2 iterations)
- User feedback stored via mcp__specter__store_user_feedback
- Agents retrieve all feedback (critic + user) via mcp__specter__get_feedback
- User feedback takes priority over critic suggestions when conflicts exist

Ready for production deployment with validated quality scores and comprehensive test coverage.
"""
