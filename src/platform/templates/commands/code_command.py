from src.platform.models import CodeCommandTools


def generate_code_command_template(tools: CodeCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [project-name] [phase-name]
description: Transform Phases into production-ready code through parallel research, implementation planning, and TDD development
---

# /respec-code Command: Implementation Orchestration

## Overview
Orchestrate the complete implementation workflow, transforming Phases into production-ready code through parallel research synthesis, implementation planning, and TDD-driven code development with comprehensive quality validation.

{tools.mcp_tools_reference}

## Workflow Steps

### 1. Extract Command Arguments and Locate Phase File

Parse command arguments and locate phase file using partial name:

#### Step 1.1: Parse arguments

```text
PROJECT_NAME = [first argument from command - the project name]
PHASE_NAME_PARTIAL = [second argument from command - partial phase name]
```

#### Step 1.2: Search file system for matching phase files

```text
SPEC_GLOB_PATTERN = ".respec-ai/projects/{{PROJECT_NAME}}/respec-phases/{{PHASE_NAME_PARTIAL}}*.md"
SPEC_FILE_MATCHES = Glob(pattern=SPEC_GLOB_PATTERN)
```

#### Step 1.3: Handle multiple matches

```text
IF count(SPEC_FILE_MATCHES) == 0:
  ERROR: "No Phase files found matching '{{PHASE_NAME_PARTIAL}}' in project {{PROJECT_NAME}}"
  SUGGEST: "Verify the phase name or check .respec-ai/projects/{{PROJECT_NAME}}/respec-phases/"
  EXIT: Workflow terminated

ELIF count(SPEC_FILE_MATCHES) == 1:
  SPEC_FILE_PATH = SPEC_FILE_MATCHES[0]

ELSE:
  (Multiple matches - use interactive selection)
  Use AskUserQuestion tool to present options:
    Question: "Multiple phase files match '{{PHASE_NAME_PARTIAL}}'. Which one do you want to use?"
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
```

#### Step 1.4: Extract canonical name from file path

```text
PHASE_NAME = [basename of SPEC_FILE_PATH without .md extension]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-2a")
- PHASE_NAME is the canonical name extracted from file path
- PROJECT_NAME is used for all MCP storage operations
- All subsequent operations use PHASE_NAME (canonical)

### 2. Load and Store Existing Spec

Load phase from file system, store in MCP:

#### Step 2.1: Read phase using canonical name

```text
PHASE_MARKDOWN = Read({{SPEC_FILE_PATH}})
```

#### Step 2.2: Store in MCP using canonical phase name

```text
{tools.store_phase_document}

Display to user: "✓ Loaded existing phase: {{PHASE_NAME}}"
```

**Important**:
- SPEC_FILE_PATH is the full path from Step 1
- PHASE_NAME is the canonical name extracted from file path
- Phase is now in MCP storage for build workflow

**Note**: Build plans are not stored in external platforms - they only exist in MCP during the build workflow.

### 4. Phase Retrieval and Validation
Retrieve and validate completed Phase from /respec-phase command:

#### Retrieve Phase
```text
TECHNICAL_PHASE = {tools.get_phase_document}
IF TECHNICAL_PHASE not found:
  ERROR: "No Phase found: [PHASE_NAME]"
  SUGGEST: "Run '/respec-phase [PROJECT_NAME] [PHASE_NAME]' to create Phase first"
  EXIT: Graceful failure with guidance

SPEC_OBJECTIVES = [Extract from Phase Objectives section]
RESEARCH_REQUIREMENTS = [Extract from Phase Research Requirements section]
TECH_STACK = [Extract from Phase Technology Stack section]
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
{tools.initialize_refinement_loop_inline_doc}
```text
PLANNING_LOOP_ID = {tools.initialize_planning_loop}

State to maintain:
- planning_loop_id: For Phase storage and retrieval
```

#### Planning Refinement Cycle
```text
Invoke task-planner agent with:
- planning_loop_id: {{PLANNING_LOOP_ID}}
- research_file_paths: {{COMPLETE_DOCUMENTATION_PATHS}}
- project_name: {{PROJECT_NAME}}
- phase_name: {{PHASE_NAME}}

Agent will autonomously:
1. Read .respec-ai/coding-standards.md (if exists)
2. Retrieve Phase via MCP
3. Retrieve existing Phase via MCP (empty on first iteration)
4. Retrieve critic feedback via MCP (none on first iteration)
5. Retrieve user feedback via MCP (if stagnation occurred)
6. Read research briefs from file paths
7. Generate or refine Phase
8. Store Phase via MCP
9. Exit

Expected: Phase stored in MCP with planning_loop_id
```

#### Planning Quality Assessment
```text
Invoke task-critic agent with:
- planning_loop_id: {{PLANNING_LOOP_ID}}
- project_name: {{PROJECT_NAME}}
- phase_name: {{PHASE_NAME}}

Agent will autonomously:
1. Retrieve Phase via MCP
2. Retrieve Phase via MCP
3. Retrieve previous critic feedback via MCP (for progress tracking)
4. Assess Phase against FSDD criteria (5 categories, 100 points total)
5. Calculate quality score (0-100)
6. Generate CriticFeedback markdown
7. Store CriticFeedback via MCP
8. Exit

Expected: CriticFeedback with Overall Score stored in MCP
```

#### MCP Planning Decision
```text
PLANNING_DECISION_RESPONSE = {tools.decide_planning_action}
PLANNING_DECISION = PLANNING_DECISION_RESPONSE.status

Note: MCP Server retrieves latest score from task-critic feedback internally.
No need to retrieve or pass score from command.

Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

### 7. Planning Decision Handling

**Follow PLANNING_DECISION exactly. Do not override based on score assessment.**

```text
IF PLANNING_DECISION == "refine":
  Re-invoke task-planner agent (same parameters).
  Re-invoke task-critic agent.
  Call MCP decision again.

ELIF PLANNING_DECISION == "complete":
  Proceed to Step 8.

ELIF PLANNING_DECISION == "user_input":
  Retrieve Phase and feedback (count=2).
  Present PLAN_QUALITY_SCORE, Key Issues, and Recommendations to user.
  Request technical guidance (approach preferences, strategies, accept/proceed).
  Store user feedback: {tools.store_user_feedback})
  Re-invoke task-planner agent.
  Re-invoke task-critic agent.
  Call MCP decision again.
```

### 7.5. Process Architectural Override Proposals

**CRITICAL**: Check for override proposals after planning completion, before starting code implementation.

After planning decision is "complete", check for architectural override proposals:

Retrieve Phase to check for override proposals:
```text
PHASE_MARKDOWN = {tools.get_task_document}
```

Check if Phase contains "Architectural Override Proposals" section:
```text
IF PHASE_MARKDOWN contains "## Architectural Override Proposals" section:
  (Extract override proposals content)
  OVERRIDE_PROPOSALS = [Extract content from "## Architectural Override Proposals" section]

  (Check if section has actual content - not just header)
  IF OVERRIDE_PROPOSALS is not empty AND not just placeholder text:
    (STOP build workflow - architectural changes require user approval)

    Display to user:
    "⚠️ Build-planner has identified potential architecture improvements.

    {{OVERRIDE_PROPOSALS}}

    This requires updating Phase. Choose action:
    1. Approve proposal → Re-run /respec-phase to update architecture
    2. Reject proposal → Continue with current phase as-is
    3. Modify proposal → Adjust and re-run /respec-phase

    Build workflow paused until Phase updated.

    To approve and update:
      /respec-phase {{PROJECT_NAME}} {{PHASE_NAME}} \"[your instructions based on proposal]\"

    To reject and proceed with current phase:
      Re-run /respec-code {{PROJECT_NAME}} {{PHASE_NAME}} --ignore-overrides"

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
- Architectural changes MUST route through /respec-phase workflow
- Phase must remain consistent across refinement loop passes
- Any changes to architecture, technology stack, or design decisions require phase update
- If user rejects override, task-planner proceeds with original phase constraints

**Override Proposal Format** (in Phase):
```markdown
## Architectural Override Proposals

**Current Phase Decision**: [What phase currently specifies]
**Proposed Change**: [What task-planner recommends instead]

**Justification**:
- Research: [Evidence from documentation/research that supports change]
- Trade-off: [Why original phase concern no longer applies]
- Impact: [Which phase sections would need updating]

**Next Action Required**: User must approve/reject via /respec-phase
```

### 8. Coding Loop Initialization and Refinement
Set up and execute MCP-managed code quality refinement:

#### Initialize Coding Loop
```text
CODING_LOOP_ID = {tools.initialize_coding_loop}

State to maintain (CRITICAL - TWO loop IDs):
- planning_loop_id: For retrieving Phase
- coding_loop_id: For code feedback storage/retrieval
```

#### Code Implementation Cycle
```text
Invoke task-coder agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- planning_loop_id: {{PLANNING_LOOP_ID}} (CRITICAL - for Phase retrieval)
- project_name: {{PROJECT_NAME}}
- phase_name: {{PHASE_NAME}}

Agent will autonomously:
1. Read .respec-ai/coding-standards.md (if exists, otherwise use Phase Code Standards)
2. Retrieve Phase via MCP using planning_loop_id
3. Retrieve Phase via MCP
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
Invoke task-reviewer agent with:
- coding_loop_id: {{CODING_LOOP_ID}}
- planning_loop_id: {{PLANNING_LOOP_ID}} (CRITICAL - for Phase retrieval)
- project_name: {{PROJECT_NAME}}
- phase_name: {{PHASE_NAME}}

Agent will autonomously:
1. Retrieve Phase via MCP using planning_loop_id
2. Retrieve Phase via MCP
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
CODING_DECISION_RESPONSE = {tools.decide_coding_action}
CODING_DECISION = CODING_DECISION_RESPONSE.status

Note: MCP Server retrieves latest score from task-reviewer feedback internally.
No need to retrieve or pass score from command.

Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

### 9. Coding Decision Handling

**Follow CODING_DECISION exactly. Do not override based on score assessment.**

```text
IF CODING_DECISION == "refine":
  Re-invoke task-coder agent (same parameters).
  Re-invoke task-reviewer agent.
  Call MCP decision again.

ELIF CODING_DECISION == "complete":
  Proceed to Step 10.

ELIF CODING_DECISION == "user_input":
  Retrieve Phase and feedback (count=2).
  Present CODE_QUALITY_SCORE, Test Results, Key Issues, and Recommendations to user.
  Request guidance (quality concerns, alternative approaches, accept/complete, constraints).
  Store user feedback: {tools.store_user_feedback})
  Re-invoke task-coder agent.
  Re-invoke task-reviewer agent.
  Call MCP decision again.
```

### 10. Integration & Documentation
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
- Iterations: {{PLANNING_ITERATION_COUNT}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- MyPy: {{MYPY_STATUS}}
- Ruff: {{RUFF_STATUS}}

Implementation artifacts:
- Phase: Available via planning_loop_id={{PLANNING_LOOP_ID}}
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
- **Code Quality Evaluation**: Assessed by task-reviewer agent
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
2. Type Checking Clean: MyPy reports zero errors
3. Linting Clean: Ruff reports zero issues
4. Test Coverage: Adequate coverage of critical paths
5. Phase Alignment: File structure and features match plan
6. Phase Requirements: All objectives implemented

Note: Loop decisions determined by MCP Server based on scoring and configuration

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No Phase found: [PHASE_NAME]"
Suggest: "/respec-phase [PROJECT_NAME] [PHASE_NAME] to create Phase"
Exit gracefully with guidance
```

#### Research Synthesis Failures
```text
IF some research-synthesizer agents fail:
  Continue with available documentation
  Note missing research areas in DOCUMENTATION_PATHS
  Flag gaps in Phase for user awareness
  Proceed with available research
```

#### Planning Loop Failures
```text
IF task-planner fails:
  Retry once with simplified context
  Create minimal Phase from Phase
  Note limitations and suggest manual review

IF task-critic fails:
  Continue without quality assessment
  Use single-pass Phase
  Warn user that quality not validated
  Suggest manual review before coding
```

#### Coding Loop Failures
```text
IF task-coder fails:
  Preserve git commits for rollback
  Report failure with TodoList state
  Provide diagnostic information
  Suggest manual intervention

IF task-reviewer fails:
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
- **Validating Phase completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Maintaining dual loop IDs** (planning_loop_id + coding_loop_id)
- **Handling MCP Server responses** without evaluating quality scores
- **Managing user feedback** during stagnation scenarios
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **task-planner**: Phase generation with research integration (MCP access)
- **task-critic**: Phase quality assessment (80% threshold)
- **task-coder**: TDD code implementation with platform integration (MCP access + platform tools)
- **task-reviewer**: Code quality assessment (95% threshold)
- **research-synthesizer**: Parallel research brief generation
- **MCP Server**: Decision logic, threshold management, state storage

## Workflow Enhancements

### Dual Loop Architecture
- Separate planning loop (Phase refinement) and coding loop (code refinement)
- planning_loop_id used for Phase storage/retrieval by all agents
- coding_loop_id used for code feedback storage/retrieval
- Agents receive both IDs and use appropriately

### Coding Standards Integration
- task-coder reads .respec-ai/coding-standards.md on initialization
- User-customizable coding standards applied to all generated code
- Fallback to Phase Code Standards if file doesn't exist

### TDD Enforcement
- Strict test-first discipline enforced by task-coder agent
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
