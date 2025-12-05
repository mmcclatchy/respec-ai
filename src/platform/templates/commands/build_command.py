from src.platform.models import BuildCommandTools


def generate_build_command_template(tools: BuildCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [project-name] [spec-name]
description: Transform technical specifications into production-ready code through parallel research, implementation planning, and TDD development
---

# /respec-build Command: Implementation Orchestration

## Overview
Orchestrate the complete implementation workflow, transforming technical specifications into production-ready code through parallel research synthesis, implementation planning, and TDD-driven code development with comprehensive quality validation.

## Workflow Steps

### 1. Extract Command Arguments and Locate Spec File

Parse command arguments and locate spec file using partial name:

```text
# Step 1.1: Parse arguments
PROJECT_NAME = [first argument from command - the project name]
SPEC_NAME_PARTIAL = [second argument from command - partial spec name]

# Step 1.2: Search file system for matching spec files
SPEC_GLOB_PATTERN = ".respec-ai/projects/{{PROJECT_NAME}}/respec-specs/{{SPEC_NAME_PARTIAL}}*.md"
SPEC_FILE_MATCHES = Glob(pattern=SPEC_GLOB_PATTERN)

# Step 1.3: Handle multiple matches
IF count(SPEC_FILE_MATCHES) == 0:
  ERROR: "No specification files found matching '{{SPEC_NAME_PARTIAL}}' in project {{PROJECT_NAME}}"
  SUGGEST: "Verify the spec name or check .respec-ai/projects/{{PROJECT_NAME}}/respec-specs/"
  EXIT: Workflow terminated

ELIF count(SPEC_FILE_MATCHES) == 1:
  SPEC_FILE_PATH = SPEC_FILE_MATCHES[0]

ELSE:
  # Multiple matches - use interactive selection
  Use AskUserQuestion tool to present options:
    Question: "Multiple spec files match '{{SPEC_NAME_PARTIAL}}'. Which one do you want to use?"
    Header: "Select Spec"
    multiSelect: false
    Options: [
      {{
        "label": "{{SPEC_FILE_MATCHES[0]}}",
        "description": "Use: {{SPEC_FILE_MATCHES[0]}}"
      }},
      {{
        "label": "{{SPEC_FILE_MATCHES[1]}}",
        "description": "Use: {{SPEC_FILE_MATCHES[1]}}"
      }},
      ... for all matches
    ]

  SPEC_FILE_PATH = [selected file path from AskUserQuestion response]

# Step 1.4: Extract canonical name from file path
SPEC_NAME = [basename of SPEC_FILE_PATH without .md extension]

Display to user: "✓ Located spec file: {{SPEC_NAME}}"
```

**Important**:
- SPEC_NAME_PARTIAL is the user input (e.g., "phase-2a")
- SPEC_NAME is the canonical name extracted from file path
- PROJECT_NAME is used for all MCP storage operations
- All subsequent operations use SPEC_NAME (canonical)

### 2. Load and Store Existing Spec

Load spec from file system, store in MCP:

```text
# Step 2.1: Read spec using canonical name
SPEC_MARKDOWN = Read({{SPEC_FILE_PATH}})

# Step 2.2: Store in MCP using canonical spec name
mcp__respec-ai__store_spec(
  project_name=PROJECT_NAME,
  spec_name=SPEC_NAME,
  spec_markdown=SPEC_MARKDOWN
)

Display to user: "✓ Loaded existing spec: {{SPEC_NAME}}"
```

**Important**:
- SPEC_FILE_PATH is the full path from Step 1
- SPEC_NAME is the canonical name extracted from file path
- Spec is now in MCP storage for build workflow

**Note**: Build plans are not stored in external platforms - they only exist in MCP during the build workflow.

### 3. Verify Canonical Spec Name

Verify spec is correctly stored in MCP with canonical name:

```text
# Call resolve_spec_name for validation only
RESOLVE_RESULT = mcp__respec-ai__resolve_spec_name(
  project_name=PROJECT_NAME,
  partial_name=SPEC_NAME
)

IF RESOLVE_RESULT['count'] != 1:
  ERROR: "Spec storage validation failed - expected 1 match for '{{SPEC_NAME}}', got {{RESOLVE_RESULT['count']}}"
  DIAGNOSTIC: Check that Step 2 (Load and Store) completed successfully
  EXIT: Workflow terminated

# Validation passed - canonical name matches MCP storage
Display to user: "✓ Using specification: {{SPEC_NAME}}"
```

**Important**:
- resolve_spec_name is now used for VALIDATION only, not resolution
- Confirms storage succeeded with correct canonical name from Step 1
- Fails loudly if mismatch between file system and MCP

### 4. Specification Retrieval and Validation
Retrieve and validate completed TechnicalSpec from /respec-spec command:

#### Retrieve TechnicalSpec
```text
TECHNICAL_SPEC = mcp__respec-ai__get_spec_markdown(PROJECT_NAME, SPEC_NAME)
IF TECHNICAL_SPEC not found:
  ERROR: "No technical specification found: [SPEC_NAME]"
  SUGGEST: "Run '/respec-spec [PROJECT_NAME] [SPEC_NAME]' to create technical specification first"
  EXIT: Graceful failure with guidance

SPEC_OBJECTIVES = [Extract from TechnicalSpec Objectives section]
RESEARCH_REQUIREMENTS = [Extract from TechnicalSpec Research Requirements section]
TECH_STACK = [Extract from TechnicalSpec Technology Stack section]
```

### 5. Parallel Research Orchestration
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

### 6. Planning Loop Initialization and Refinement
Set up and execute MCP-managed planning quality refinement:

#### Initialize Planning Loop
```text
PLANNING_LOOP_ID = mcp__respec-ai__initialize_refinement_loop(loop_type='build_plan')

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
1. Read .respec-ai/coding-standards.md (if exists)
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
PLANNING_DECISION = mcp__respec-ai__decide_loop_next_action(
    loop_id=PLANNING_LOOP_ID,
    current_score=PLAN_QUALITY_SCORE
)

Returns:
- "refine" if score < 80%
- "complete" if score >= 80%
- "user_input" if stagnation detected (<5 points improvement over 2 iterations)
```

### 7. Planning Decision Handling

**Follow PLANNING_DECISION exactly. Do not override based on score assessment.**

#### If PLANNING_DECISION == "refine"
Re-invoke build-planner agent (same parameters).
Re-invoke build-critic agent.
Call MCP decision again.

#### If PLANNING_DECISION == "complete"
Proceed to Step 8.

#### If PLANNING_DECISION == "user_input"
Retrieve BuildPlan and feedback (count=2).
Present PLAN_QUALITY_SCORE, Key Issues, and Recommendations to user.
Request technical guidance (approach preferences, strategies, accept/proceed).
Store user feedback: mcp__respec-ai__store_user_feedback(PLANNING_LOOP_ID, USER_FEEDBACK_MARKDOWN)
Re-invoke build-planner agent.
Re-invoke build-critic agent.
Call MCP decision again.

### 7.5. Process Architectural Override Proposals

**CRITICAL**: Check for override proposals after planning completion, before starting code implementation.

After planning decision is "complete", check for architectural override proposals:

```text
# Retrieve BuildPlan to check for override proposals
BUILD_PLAN_MARKDOWN = mcp__respec-ai__get_build_plan_markdown(
    planning_loop_id=PLANNING_LOOP_ID
)

# Check if BuildPlan contains "Architectural Override Proposals" section
IF BUILD_PLAN_MARKDOWN contains "## Architectural Override Proposals" section:
  # Extract override proposals content
  OVERRIDE_PROPOSALS = [Extract content from "## Architectural Override Proposals" section]

  # Check if section has actual content (not just header)
  IF OVERRIDE_PROPOSALS is not empty AND not just placeholder text:
    # STOP build workflow - architectural changes require user approval

    Display to user:
    "⚠️ Build-planner has identified potential architecture improvements.

    {{OVERRIDE_PROPOSALS}}

    This requires updating TechnicalSpec. Choose action:
    1. Approve proposal → Re-run /respec-spec to update architecture
    2. Reject proposal → Continue with current spec as-is
    3. Modify proposal → Adjust and re-run /respec-spec

    Build workflow paused until TechnicalSpec updated.

    To approve and update:
      /respec-spec {{PROJECT_NAME}} {{SPEC_NAME}} \"[your instructions based on proposal]\"

    To reject and proceed with current spec:
      Re-run /respec-build {{PROJECT_NAME}} {{SPEC_NAME}} --ignore-overrides"

    EXIT: Workflow suspended pending user decision
  ELSE:
    # Section exists but is empty - proceed normally
    Proceed to Step 8

ELSE:
  # No override proposals section - proceed normally
  Proceed to Step 8
```

**Important Notes**:
- Build-planner is a subagent with NO user interaction capability
- Architectural changes MUST route through /respec-spec workflow
- TechnicalSpec must remain consistent across refinement loop passes
- Any changes to architecture, technology stack, or design decisions require spec update
- If user rejects override, build-planner proceeds with original spec constraints

**Override Proposal Format** (in BuildPlan):
```markdown
## Architectural Override Proposals

**Current Spec Decision**: [What spec currently specifies]
**Proposed Change**: [What build-planner recommends instead]

**Justification**:
- Research: [Evidence from documentation/research that supports change]
- Trade-off: [Why original spec concern no longer applies]
- Impact: [Which spec sections would need updating]

**Next Action Required**: User must approve/reject via /respec-spec
```

### 8. Coding Loop Initialization and Refinement
Set up and execute MCP-managed code quality refinement:

#### Initialize Coding Loop
```text
CODING_LOOP_ID = mcp__respec-ai__initialize_refinement_loop(loop_type='build_code')

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
1. Read .respec-ai/coding-standards.md (if exists, otherwise use BuildPlan Code Standards)
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
CODING_DECISION = mcp__respec-ai__decide_loop_next_action(
    loop_id=CODING_LOOP_ID,
    current_score=CODE_QUALITY_SCORE
)

Returns:
- "refine" if score < 95%
- "complete" if score >= 95%
- "user_input" if stagnation detected (<5 points improvement over 2 iterations)
```

### 9. Coding Decision Handling

**Follow CODING_DECISION exactly. Do not override based on score assessment.**

#### If CODING_DECISION == "refine"
Re-invoke build-coder agent (same parameters).
Re-invoke build-reviewer agent.
Call MCP decision again.

#### If CODING_DECISION == "complete"
Proceed to Step 10.

#### If CODING_DECISION == "user_input"
Retrieve BuildPlan and feedback (count=2).
Present CODE_QUALITY_SCORE, Test Results, Key Issues, and Recommendations to user.
Request guidance (quality concerns, alternative approaches, accept/complete, constraints).
Store user feedback: mcp__respec-ai__store_user_feedback(CODING_LOOP_ID, USER_FEEDBACK_MARKDOWN)
Re-invoke build-coder agent.
Re-invoke build-reviewer agent.
Call MCP decision again.

### 10. Integration & Documentation
Complete implementation workflow and update specification:

#### Generate Implementation Summary
```text
Retrieve final state:
- BuildPlan: mcp__respec-ai__get_build_plan_markdown(PLANNING_LOOP_ID)
- Final Feedback: mcp__respec-ai__get_feedback(CODING_LOOP_ID, count=1)

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
Update specification status and implementation details using mcp__respec-ai__store_spec:

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
- Spec Status: Updated via mcp__respec-ai__store_spec

Ready for deployment."
```

## Spec Name Normalization Rules

**IMPORTANT:** Spec names are automatically normalized to kebab-case:

**File System → MCP Normalization:**
- Convert to lowercase: `Phase-1` → `phase-1`
- Replace spaces/underscores with hyphens: `phase 1` → `phase-1`
- Remove special characters: `phase-1!` → `phase-1`
- Collapse multiple hyphens: `phase--1` → `phase-1`
- Strip leading/trailing hyphens: `-phase-1-` → `phase-1`

**Critical:** The H1 header in spec markdown MUST match the normalized file name:
- File: `phase-2a-neo4j-schema-and-llama-index-integration.md`
- H1 header: `# Technical Specification: phase-2a-neo4j-schema-and-llama-index-integration`
- Mismatch will cause storage/retrieval failures

**Build agents:** Use normalized spec names when retrieving specifications via MCP.

## Quality Gates

### Quality Assessment
- **BuildPlan Evaluation**: Assessed by build-critic agent
- **Code Quality Evaluation**: Assessed by build-reviewer agent
- **Loop Decisions**: Made by MCP Server based on configuration
- **Thresholds and Limits**: Managed by MCP Server

### Assessment Criteria

**BuildPlan Assessment Criteria**:
1. Plan Completeness: All sections populated with substantive content
2. TechnicalSpec Alignment: Matches objectives, scope, architecture
3. Test Strategy Clarity: TDD approach and test organization defined
4. Implementation Sequence Logic: Dependencies respec-aited, phases logical
5. Technology Appropriateness: Stack suitable for requirements

**Code Quality Assessment Criteria**:
1. Tests Passing: All tests execute successfully
2. Type Checking Clean: MyPy reports zero errors
3. Linting Clean: Ruff reports zero issues
4. Test Coverage: Adequate coverage of critical paths
5. BuildPlan Alignment: File structure and features match plan
6. TechnicalSpec Requirements: All objectives implemented

Note: Loop decisions determined by MCP Server based on scoring and configuration

## Error Handling

### Graceful Degradation Patterns

#### TechnicalSpec Not Available
```text
Display: "No technical specification found: [SPEC_NAME]"
Suggest: "/respec-spec [PROJECT_NAME] [SPEC_NAME] to create technical specification"
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
- build-coder reads .respec-ai/coding-standards.md on initialization
- User-customizable coding standards applied to all generated code
- Fallback to BuildPlan Code Standards if file doesn't exist

### TDD Enforcement
- Strict test-first discipline enforced by build-coder agent
- Tests must fail before implementation proceeds
- Tests must pass before considering feature complete
- Commit after each iteration for rollback capability

### User Feedback During Stagnation
- User input requested when quality plateaus (<5 points over 2 iterations)
- User feedback stored via mcp__respec-ai__store_user_feedback
- Agents retrieve all feedback (critic + user) via mcp__respec-ai__get_feedback
- User feedback takes priority over critic suggestions when conflicts exist

Ready for production deployment with validated quality scores and comprehensive test coverage.
"""
