# /specter-build Workflow Implementation Plan

**Status**: Planning Complete - Ready for Implementation
**Date**: 2025-10-22
**Version**: 1.0

## Overview

This document outlines the complete implementation plan for the `/specter-build` command workflow. The workflow implements a dual-loop refinement system (planning loop + coding loop) that takes a TechnicalSpec and produces production-ready code following TDD methodology.

## Workflow Architecture

### High-Level Flow

```text
User: /specter-build [spec_name]
  ↓
Main Agent (build_command.py)
  ├→ Retrieve TechnicalSpec
  ├→ Launch Parallel Research (research-synthesizer agents)
  ├→ Planning Loop (build_planner ↔ build_critic)
  │   └→ MCP decides: refine/complete/user_input
  ├→ Coding Loop (build_coder ↔ build_reviewer)
  │   └→ MCP decides: refine/complete/user_input
  └→ Update TechnicalSpec + Platform Integration
```

### Agent Workflow Pattern

All agents follow the same autonomous pattern:

```text
Agent Invocation:
  ↓
Retrieve documents from MCP autonomously
  ↓
Process (plan, critique, code, review)
  ↓
Store results to MCP
  ↓
Exit
```

**Main Agent Role**: Pure orchestrator
- Receives MCP decisions
- Acts on decisions (no thinking, just routing)
- Handles user feedback collection
- Maintains minimal state (loop IDs only)

---

## Phase-by-Phase Implementation

### PHASE 1: User Invocation & Initialization

#### Step 1.1: User Command Submission
- **Actor**: User
- **Action**: Execute `/specter-build [spec_name]`
- **Implementation**: No changes needed (command parsing handled by platform)

#### Step 1.2: Main Agent Initialization
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Parse command, validate spec_name, initialize workflow
- **Implementation Needed**:
  - Parse spec_name from command
  - Initialize workflow context
  - Platform tools already pre-configured in frontmatter

---

### PHASE 2: Specification Retrieval

#### Step 2.1: Retrieve TechnicalSpec
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Call `mcp__specter__get_spec_markdown(project_id, spec_name)`
- **Implementation Needed**:
  - Add error handling for non-existent spec
  - Validate spec exists before proceeding

#### Step 2.2: Parse Specification Content
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Parse TechnicalSpec markdown into structured object
- **Implementation Needed**:
  - Call `TechnicalSpec.parse_markdown(spec_markdown)`
  - Validate required fields are present (architecture, tech_stack, research_requirements)

---

### PHASE 3: Research Orchestration (Parallel Execution)

#### Step 3.1: Extract Research Requirements
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Extract research items from TechnicalSpec `research_requirements` field
- **Implementation Needed**:
  - Parse `research_requirements` markdown section
  - Extract individual research queries (likely bulleted list or numbered list)
  - Create list of research queries for parallel execution

**Example TechnicalSpec Research Requirements Section**:
```markdown
### Research Requirements

- FastAPI async best practices and error handling patterns
- PostgreSQL schema design for high-concurrency applications
- React state management with Redux Toolkit
```

**Parsing Logic Needed**:

```text
Extract research items from TechnicalSpec markdown:
  1. Get research_requirements field from parsed TechnicalSpec
  2. Parse markdown to extract list items (bulleted or numbered)
  3. Result: list of research query strings
     Example: ["FastAPI async best practices...", "PostgreSQL schema design...", ...]
```

#### Step 3.2: Launch Parallel Research Agents
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Invoke multiple research-synthesizer agents in parallel
- **Implementation Needed**:
  - **CRITICAL**: Use **single message** with **multiple Task calls** (one per research item)
  - Each Task invokes research-synthesizer with one research query
  - Collect file paths returned by each agent

**Implementation Pattern**:
```text
Single response message containing:
  Task call 1: research-synthesizer query="FastAPI async best practices..."
  Task call 2: research-synthesizer query="PostgreSQL schema design..."
  Task call 3: research-synthesizer query="React state management..."
```

**Expected Output**:
Each research-synthesizer returns a file path:
- `~/.claude/best-practices/fastapi-async-patterns.md`
- `~/.claude/best-practices/postgresql-schema-design.md`
- `~/.claude/best-practices/react-state-management.md`

#### Step 3.3: Collect Research Paths
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Collect file paths from research-synthesizer agents
- **Implementation Needed**:
  - Aggregate file paths into list
  - Store list for passing to build_planner agent
  - No synthesis needed (build_planner will read documents directly)

---

### PHASE 4: Planning Loop (build_planner ↔ build_critic Refinement)

#### Step 4.1: Initialize Planning Refinement Loop
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Call `mcp__specter__initialize_refinement_loop(loop_type='build_plan')`
- **Implementation Needed**:
  - Store returned `planning_loop_id` in Main Agent state
  - This ID will be passed to all planning agents

#### Step 4.2: Invoke build_planner Agent (Iteration 1)
- **Actor**: build_planner agent
- **File**: `services/templates/agents/build_planner.py` (**NEEDS CREATION**)
- **Action**: Create BuildPlan from TechnicalSpec + research briefs

**Agent Workflow**:
1. Retrieve TechnicalSpec via `mcp__specter__get_spec_markdown(project_id, spec_name)`
2. Retrieve BuildPlan via `mcp__specter__get_build_plan_markdown(planning_loop_id)` (empty if first iteration)
3. Retrieve previous critic feedback via `mcp__specter__get_critic_feedback(planning_loop_id)` (none if first iteration)
4. Read research briefs from file paths (provided as agent parameter)
5. Generate BuildPlan markdown matching [BuildPlan structure](services/models/build_plan.py)
6. Store BuildPlan via `mcp__specter__store_build_plan(planning_loop_id, plan_markdown)`
7. Exit

**Agent Inputs** (passed by Main Agent):
- `planning_loop_id` (for MCP retrieval/storage)
- `research_file_paths` (list of paths to research documents)
- `project_id` (for TechnicalSpec retrieval)
- `spec_name` (for TechnicalSpec retrieval)

**Tools Needed** (in agent frontmatter):
- `mcp__specter__get_spec_markdown`
- `mcp__specter__get_build_plan_markdown`
- `mcp__specter__get_critic_feedback`
- `mcp__specter__store_build_plan`
- `Read` (for reading research briefs)

**Instructions Focus**:
- Reference research documents when making planning decisions (don't synthesize)
- Follow BuildPlan structure exactly
- On refinement iterations: incorporate critic feedback into plan improvements

#### Step 4.3: Invoke build_critic Agent (Iteration 1)
- **Actor**: build_critic agent
- **File**: `services/templates/agents/build_critic.py` (**NEEDS CREATION**)
- **Action**: Assess BuildPlan quality against FSDD criteria

**Agent Workflow**:
1. Retrieve BuildPlan via `mcp__specter__get_build_plan_markdown(planning_loop_id)`
2. Retrieve previous critic feedback via `mcp__specter__get_critic_feedback(planning_loop_id)` (to track progress)
3. Retrieve TechnicalSpec via `mcp__specter__get_spec_markdown(project_id, spec_name)`
4. Critique plan against FSDD criteria
5. Determine score (0-100, threshold: 80%)
6. Generate CriticFeedback markdown (score, assessment, issues, recommendations)
7. Store feedback via `mcp__specter__store_critic_feedback(planning_loop_id, feedback_markdown)`
8. Exit

**Agent Inputs** (passed by Main Agent):
- `planning_loop_id`
- `project_id`
- `spec_name`

**Tools Needed** (in agent frontmatter):
- `mcp__specter__get_build_plan_markdown`
- `mcp__specter__get_critic_feedback`
- `mcp__specter__get_spec_markdown`
- `mcp__specter__store_critic_feedback`

**FSDD Criteria for Assessment** (80% threshold):
- Plan completeness (all BuildPlan sections populated)
- Alignment with TechnicalSpec (matches objectives, scope, architecture)
- Test strategy clarity (TDD approach defined)
- Implementation sequence logic (dependencies respected)
- Technology stack appropriateness (matches spec requirements)

**CriticFeedback Structure Needed**:
  ```markdown
  ## Planning Assessment

  ### Overall Score
  [0-100 score]

  ### Assessment Summary
  [Brief summary of plan quality]

  ### Detailed Feedback
  [Section-by-section critique]

  ### Key Issues
  - [Issue 1]
  - [Issue 2]

  ### Recommendations
  - [Recommendation 1]
  - [Recommendation 2]
  ```

#### Step 4.4: MCP Loop Decision
- **Actor**: MCP Server
- **Action**: Call `mcp__specter__decide_loop_next_action(planning_loop_id, current_score)`
- **Implementation**: Already exists (no changes needed)
- **Returns**: MCPResponse with status:
  - `refine` if score < 80%
  - `complete` if score ≥ 80%
  - `user_input` if stagnation detected (<5 points improvement over 2 iterations)

#### Step 4.5: Handle Refinement Decision
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Implementation Needed**:

**If status = "refine"**:
- Re-invoke build_planner agent (same parameters)
- Agent will retrieve previous critic feedback and incorporate into plan
- Re-invoke build_critic agent
- Call MCP decision again
- Repeat until complete or user_input

**If status = "complete"**:
- Proceed to Phase 5 (Coding Loop)

**If status = "user_input"**:
- Save BuildPlan to platform (Linear/GitHub/Markdown)
- Retrieve critic feedback from MCP
- Present to user:
  - Current state recap
  - Challenges faced (from critic feedback)
  - Options for proceeding with pros/cons
  - Recommendation
- Collect user feedback
- Store user feedback via `mcp__specter__store_user_feedback(planning_loop_id, feedback_markdown)` (**NEW TOOL NEEDED**)
- Re-invoke build_planner with user feedback available

**Maximum Iterations**: 5 (per `FSDD_LOOP_BUILD_PLAN_MAX_ITERATIONS`)

---

### PHASE 5: Coding Loop (build_coder ↔ build_reviewer Refinement)

#### Step 5.1: Initialize Coding Refinement Loop
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Call `mcp__specter__initialize_refinement_loop(loop_type='build_code')`
- **Implementation Needed**:
  - Store returned `coding_loop_id` in Main Agent state
  - Main Agent now maintains TWO loop IDs: `planning_loop_id` + `coding_loop_id`

#### Step 5.2: Invoke build_coder Agent (Iteration 1 - TDD)
- **Actor**: build_coder agent
- **File**: `services/templates/agents/build_coder.py` (**NEEDS CREATION**)
- **Action**: Implement code following TDD methodology (tests first, then implementation)

**Agent Workflow**:
1. Read coding standards from `.specter/coding-standards.md` (if exists, otherwise use BuildPlan Code Standards)
2. Retrieve BuildPlan via `mcp__specter__get_build_plan_markdown(planning_loop_id)` (**NOTE**: uses planning_loop_id!)
3. Retrieve TechnicalSpec via `mcp__specter__get_spec_markdown(project_id, spec_name)`
4. Retrieve previous critic feedback via `mcp__specter__get_critic_feedback(coding_loop_id)` (if any)
5. Retrieve user feedback via `mcp__specter__get_user_feedback(coding_loop_id)` (if any)
6. Check current state of implementation (file system inspection via Read/Glob)
7. Create TodoList of actions to take (using TodoWrite tool)
8. Execute todo list following TDD (applying coding standards to all code):
   - Write tests first (using Write/Edit)
   - Run tests (using Bash: pytest) - should fail
   - Implement code (using Write/Edit)
   - Run tests (using Bash: pytest) - should pass
   - Run static analysis (using Bash: mypy, ruff)
9. Commit changes (using Bash: git add, git commit)
10. Exit upon completion of todo list

**Agent Inputs** (passed by Main Agent):
- `coding_loop_id` (for storing critic feedback)
- `planning_loop_id` (for retrieving BuildPlan - **CRITICAL**)
- `project_id`
- `spec_name`

**Tools Needed** (in agent frontmatter):
- `mcp__specter__get_build_plan_markdown`
- `mcp__specter__get_spec_markdown`
- `mcp__specter__get_critic_feedback`
- `mcp__specter__get_user_feedback` (**NEW TOOL NEEDED**)
- `Write`, `Edit`, `Read`, `Glob`
- `Bash` (pytest, mypy, ruff, git)
- `TodoWrite` (for task tracking)
- Platform tools (Linear, GitHub, Markdown - pre-configured)

**TDD Enforcement Strategy**:
- Instructions must emphasize test-first discipline
- TodoList should structure work as: write test → run test (fail) → implement → run test (pass)
- Agent should verify tests fail before implementation
- Agent should verify tests pass after implementation

**Commit Strategy**:
- Commit after each iteration (even if "half-baked")
- Commit message format: `build iteration [N]: [summary of changes]`
- Benefits: rollback capability, state tracking, audit trail

#### Step 5.3: Invoke build_reviewer Agent (Iteration 1)
- **Actor**: build_reviewer agent
- **File**: `services/templates/agents/build_reviewer.py` (**NEEDS CREATION**)
- **Action**: Review code quality, test coverage, alignment with BuildPlan/TechnicalSpec

**Agent Workflow**:
1. Retrieve BuildPlan via `mcp__specter__get_build_plan_markdown(planning_loop_id)` (**NOTE**: uses planning_loop_id!)
2. Retrieve TechnicalSpec via `mcp__specter__get_spec_markdown(project_id, spec_name)`
3. Retrieve previous critic feedback via `mcp__specter__get_critic_feedback(coding_loop_id)` (to track progress)
4. Inspect codebase (file system inspection via Read/Glob)
5. Run static analysis (Bash: mypy, ruff)
6. Run tests (Bash: pytest --cov)
7. Assess code quality against criteria:
   - All tests passing
   - Type checking clean (mypy)
   - Linting clean (ruff)
   - Test coverage adequate
   - Code matches BuildPlan structure
   - Code implements TechnicalSpec requirements
   - No regressions from previous iteration
8. Determine score (0-100, threshold: 95%)
9. Generate CriticFeedback markdown (score, assessment, issues, recommendations)
10. Store feedback via `mcp__specter__store_critic_feedback(coding_loop_id, feedback_markdown)`
11. Exit

**Agent Inputs** (passed by Main Agent):
- `coding_loop_id`
- `planning_loop_id` (**CRITICAL** - for BuildPlan access)
- `project_id`
- `spec_name`

**Tools Needed** (in agent frontmatter):
- `mcp__specter__get_build_plan_markdown`
- `mcp__specter__get_spec_markdown`
- `mcp__specter__get_critic_feedback`
- `Read`, `Glob`
- `Bash` (pytest, mypy, ruff)
- `mcp__specter__store_critic_feedback`

**95% Threshold Calibration**:
Score breakdown (suggested weighting):
- Tests passing: 30 points (all must pass)
- Type checking clean: 15 points (mypy with no errors)
- Linting clean: 10 points (ruff with no errors)
- Test coverage: 15 points (≥80% coverage)
- BuildPlan alignment: 15 points (file structure matches)
- TechnicalSpec alignment: 15 points (implements requirements)

**Minimum 95% = 95/100 points**

#### Step 5.4: MCP Loop Decision (Coding Phase)
- **Actor**: MCP Server
- **Action**: Call `mcp__specter__decide_loop_next_action(coding_loop_id, current_score)`
- **Implementation**: Already exists (no changes needed)
- **Returns**: MCPResponse with status:
  - `refine` if score < 95%
  - `complete` if score ≥ 95%
  - `user_input` if stagnation detected (<5 points improvement over 2 iterations)

#### Step 5.5: Handle Refinement Decision
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Implementation Needed**:

**If status = "refine"**:
- Re-invoke build_coder agent (same parameters)
- Agent will retrieve previous critic feedback and user feedback (if any)
- Re-invoke build_reviewer agent
- Call MCP decision again
- Repeat until complete or user_input

**If status = "complete"**:
- Proceed to Phase 6 (Integration & Documentation)

**If status = "user_input"**:
- Save current code state to platform (commit if not already committed)
- Retrieve BuildPlan from MCP (for context)
- Retrieve critic feedback from MCP
- Present to user:
  - Current implementation state recap
  - Challenges faced (from critic feedback)
  - Options for proceeding with pros/cons
  - Recommendation
- Collect user feedback
- Store user feedback via `mcp__specter__store_user_feedback(coding_loop_id, feedback_markdown)` (**NEW TOOL NEEDED**)
- Re-invoke build_coder with user feedback available

**Maximum Iterations**: 5 (per `FSDD_LOOP_BUILD_CODE_MAX_ITERATIONS`)

**Risk**: 95% threshold is high - may cause frequent stagnation. Monitor in practice and adjust if needed.

---

### PHASE 6: Integration & Documentation

#### Step 6.1: Update TechnicalSpec Status
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Update TechnicalSpec with implementation completion status
- **Implementation Needed**:
  - Retrieve TechnicalSpec via `mcp__specter__get_spec_markdown(project_id, spec_name)`
  - Update `spec_status` field to `IMPLEMENTED`
  - Optionally add metadata fields:
    - `build_planning_score`: final planning loop score
    - `build_coding_score`: final coding loop score
  - Store updated spec via `mcp__specter__store_spec(project_id, spec_name, updated_markdown)`

**Note**: Do NOT increment `iteration` field - that tracks spec refinement, not build implementation.

#### Step 6.2: Platform Integration Updates
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Update platform artifacts with implementation status
- **Implementation Needed**:

Platform tools are pre-configured in command frontmatter. Use consistent logic across platforms:

**If Linear**:
- Update issue status (In Progress → Completed or Done)
- Add comment with implementation summary
- Tool: `mcp__linear-server__update_issue`

**If GitHub**:
- Update issue with implementation summary comment
- Optionally close issue
- Tool: Bash `gh issue comment [issue_number] --body "[summary]"`

**If Markdown**:
- Update markdown file with completion status
- Append implementation summary
- Tool: `Edit` or `Write`

**Implementation Summary Content**:
- Build planning score
- Build coding score
- Total iterations (planning + coding)
- Files created/modified
- Test coverage percentage

#### Step 6.3: Generate Implementation Summary
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Create summary for user
- **Implementation Needed**:

Aggregate data:
- BuildPlan (file structure, test strategy)
- Final scores (planning, coding)
- Iteration counts
- Files created/modified (from git log or file system inspection)
- Test results (pass/fail counts, coverage)

Generate simple markdown summary (no need to overcomplicate).

#### Step 6.4: Present Completion to User
- **Actor**: Main Agent
- **File**: [build_command.py](services/templates/commands/build_command.py)
- **Action**: Display implementation summary
- **Implementation Needed**:
  - Output implementation summary as message to user
  - Include next steps (e.g., "Review code and push to remote repository")

#### Step 6.5: Cleanup Loop State
- **Implementation**: Defer to later (implementation details)
- Options to consider later:
  - Delete BuildPlan from memory
  - Archive loop state
  - Preserve for historical analysis

---

## New MCP Tools Required

### User Feedback Tools

**File**: `services/mcp/tools/user_feedback_tools.py` (**NEEDS CREATION**)

#### Tool 1: store_user_feedback
```python
async def store_user_feedback(
    loop_id: str,
    feedback_markdown: str,
    ctx: Context
) -> MCPResponse:
    """Store user feedback for a refinement loop.

    Parameters:
    - loop_id: Loop ID to store feedback for
    - feedback_markdown: User feedback in markdown format

    Returns:
    - MCPResponse: Contains loop_id, status, confirmation message
    """
```

**Storage Pattern**: Similar to critic_feedback_tools.py
- Store by loop_id: `self._user_feedback[loop_id] = feedback_markdown`
- Validate loop exists
- Return MCPResponse confirmation

#### Tool 2: get_user_feedback
```python
async def get_user_feedback(
    loop_id: str,
    ctx: Context
) -> MCPResponse:
    """Retrieve user feedback for a refinement loop.

    Parameters:
    - loop_id: Loop ID to retrieve feedback for

    Returns:
    - MCPResponse: Contains loop_id, status, feedback markdown in message field
    """
```

**Retrieval Pattern**: Similar to get_critic_feedback
- Retrieve by loop_id
- Return empty/default if no feedback exists
- Return MCPResponse with feedback in message field

**Registration**: Add to `services/platform/tool_discovery.py`

---

## Agent Template Requirements

### Dual Tool Architecture Pattern

All agent templates follow the established pattern from `roadmap.py`:

**Two Categories of Tools**:
1. **MCP Specter Tools**: Explicitly defined in frontmatter (always the same regardless of platform)
   - Example: `mcp__specter__get_spec_markdown`, `mcp__specter__store_build_plan`
   - These are hardcoded in the agent frontmatter

2. **Platform-Specific Tools**: Injected via function parameter (varies by platform: Linear/GitHub/Markdown)
   - Example: `{tools.update_task_status}` (rendered as `mcp__linear-server__update_issue` or `gh issue update` or file edit)
   - Requires `AgentTools` model in `services/platform/models.py`
   - Agent function accepts typed tools parameter

**Implementation Pattern**:
```python
# In services/platform/models.py
class MyAgentTools(BaseModel):
    platform_tool_name: str = Field(..., description='Platform-specific operation')

# In services/templates/agents/my_agent.py
def generate_my_agent_template(tools: MyAgentTools) -> str:
    return f'''---
tools:
  - mcp__specter__some_tool
  - {tools.platform_tool_name}  # Dynamically rendered
---'''
```

**When to Use**:
- Use `AgentTools` parameter **only if** agent needs platform-specific operations (creating issues, updating tasks, etc.)
- Agents that only use MCP Specter tools + built-in tools (Read, Write, Bash) don't need tools parameter
- build_coder needs platform tools (updating task status), build_planner does not

---

### Agent 1: build_planner.py

**Location**: `services/templates/agents/build_planner.py`

**Frontmatter Tools**:
```yaml
tools:
  - mcp__specter__get_spec_markdown
  - mcp__specter__get_build_plan_markdown
  - mcp__specter__get_critic_feedback
  - mcp__specter__get_user_feedback
  - mcp__specter__store_build_plan
  - Read
```

**Agent Instructions Focus**:
- Retrieve TechnicalSpec, BuildPlan (if exists), previous feedback
- Read research briefs from provided file paths
- Reference research when making planning decisions (don't synthesize)
- Generate BuildPlan following exact structure from BuildPlan model
- On refinement: incorporate critic feedback and user feedback
- Store BuildPlan to MCP

**BuildPlan Sections to Populate** (from build_plan.py):
- Project Overview (Goal, Duration, Team Size)
- Technology Stack (Primary Language, Framework, Database)
- Architecture (Development Environment, Database Schema, API Architecture, Frontend Architecture)
- Implementation (Core Features, Integration Points)
- Quality Management (Testing Strategy, Code Standards, Performance Requirements, Security Implementation)
- Metadata (Status = PLANNING)

---

### Agent 2: build_critic.py

**Location**: `services/templates/agents/build_critic.py`

**Frontmatter Tools**:
```yaml
tools:
  - mcp__specter__get_build_plan_markdown
  - mcp__specter__get_spec_markdown
  - mcp__specter__get_critic_feedback
  - mcp__specter__store_critic_feedback
  - Read
```

**Agent Instructions Focus**:
- Retrieve BuildPlan, TechnicalSpec, previous feedback
- Assess plan against FSDD criteria (80% threshold)
- Track progress from previous feedback
- Generate structured CriticFeedback with score
- Store feedback to MCP

**FSDD Assessment Criteria**:
- Plan completeness (all sections populated)
- Alignment with TechnicalSpec
- Test strategy clarity (TDD approach)
- Implementation sequence logic
- Technology stack appropriateness

**CriticFeedback Structure**:
- Overall Score (0-100)
- Assessment Summary
- Detailed Feedback (section-by-section)
- Key Issues
- Recommendations

---

### Agent 3: build_coder.py

**Location**: `services/templates/agents/build_coder.py`

**Agent Tools Model** (needs creation in `services/platform/models.py`):
```python
class BuildCoderAgentTools(BaseModel):
    update_task_status: str = Field(..., description='Platform tool for updating task/issue status')
```

**Agent Function Signature**:
```python
def generate_build_coder_template(tools: BuildCoderAgentTools) -> str:
```

**Frontmatter Tools** (dual architecture - MCP + Platform):
```yaml
tools:
  - mcp__specter__get_build_plan_markdown
  - mcp__specter__get_spec_markdown
  - mcp__specter__get_critic_feedback
  - mcp__specter__get_user_feedback
  - Write
  - Edit
  - Read
  - Glob
  - Bash
  - TodoWrite
  - {tools.update_task_status}
```

**Note**: Platform-specific tools injected via `tools` parameter, rendered dynamically based on platform (Linear/GitHub/Markdown)

**Agent Instructions Focus**:
- Retrieve BuildPlan (via planning_loop_id), TechnicalSpec, feedback
- Check current implementation state
- Create TodoList of actions (using TodoWrite)
- Follow TDD methodology strictly:
  - Write tests first
  - Run tests (should fail)
  - Implement code
  - Run tests (should pass)
  - Run static analysis
- Commit changes after iteration
- Exit upon completion

**TDD Enforcement**:
- TodoList structure: test → verify fail → implement → verify pass
- Explicit verification steps
- No implementation before tests written

**Commit Strategy**:
- After each iteration
- Format: `build iteration [N]: [summary]`

---

### Agent 4: build_reviewer.py

**Location**: `services/templates/agents/build_reviewer.py`

**Frontmatter Tools**:
```yaml
tools:
  - mcp__specter__get_build_plan_markdown
  - mcp__specter__get_spec_markdown
  - mcp__specter__get_critic_feedback
  - mcp__specter__store_critic_feedback
  - Read
  - Glob
  - Bash
```

**Agent Instructions Focus**:
- Retrieve BuildPlan (via planning_loop_id), TechnicalSpec, previous feedback
- Inspect codebase (file system)
- Run static analysis (mypy, ruff)
- Run tests with coverage (pytest --cov)
- Assess quality against 95% threshold criteria
- Track progress and detect regressions
- Generate structured CriticFeedback with score
- Store feedback to MCP

**95% Threshold Criteria**:
- Tests passing: 30 points
- Type checking clean: 15 points
- Linting clean: 10 points
- Test coverage ≥80%: 15 points
- BuildPlan alignment: 15 points
- TechnicalSpec alignment: 15 points

**CriticFeedback Structure**: Same as build_critic

---

## build_command.py Updates

**File**: `services/templates/commands/build_command.py`

### Key Implementation Points

**State Management**:

Main Agent maintains minimal state (just identifiers):

```text
- planning_loop_id (from Phase 4.1 - initialize_refinement_loop)
- coding_loop_id (from Phase 5.1 - initialize_refinement_loop)
- project_id (from command context)
- spec_name (from command parameter)
- research_file_paths (from Phase 3.2 - collected from research-synthesizer agents)
```

**Parallel Research Execution**:

Main Agent sends **single message** containing multiple Task calls:

```text
For 3 research items in TechnicalSpec:
  Message contains:
    - Task(subagent_type=research-synthesizer, query="FastAPI async best practices...")
    - Task(subagent_type=research-synthesizer, query="PostgreSQL schema design...")
    - Task(subagent_type=research-synthesizer, query="React state management...")

All 3 agents execute in parallel.
Each returns file path: ~/.claude/best-practices/[topic].md
Main Agent collects paths into list.
```

**Loop Orchestration Pattern**:

**Planning Loop Flow:**

```text
1. Main Agent invokes: Task(subagent_type=build_planner, loop_id=planning_loop_id, research_paths=..., project_id=..., spec_name=...)
2. build_planner agent executes autonomously (retrieve → process → store → exit)
3. Main Agent invokes: Task(subagent_type=build_critic, loop_id=planning_loop_id, project_id=..., spec_name=...)
4. build_critic agent executes autonomously (retrieve → process → store → exit)
5. Main Agent calls MCP tool: mcp__specter__decide_loop_next_action(planning_loop_id, current_score)
6. Main Agent receives MCPResponse with decision and acts:
   - If status="refine": Go to step 1 (repeat loop)
   - If status="complete": Exit planning loop, proceed to coding loop
   - If status="user_input": Handle user feedback (see User Input Handling), then go to step 1
7. Maximum 5 iterations enforced by MCP
```

**Coding Loop Flow:**

```text
1. Main Agent invokes: Task(subagent_type=build_coder, coding_loop_id=..., planning_loop_id=..., project_id=..., spec_name=...)
2. build_coder agent executes autonomously (retrieve → process → store → exit)
3. Main Agent invokes: Task(subagent_type=build_reviewer, coding_loop_id=..., planning_loop_id=..., project_id=..., spec_name=...)
4. build_reviewer agent executes autonomously (retrieve → process → store → exit)
5. Main Agent calls MCP tool: mcp__specter__decide_loop_next_action(coding_loop_id, current_score)
6. Main Agent receives MCPResponse with decision and acts:
   - If status="refine": Go to step 1 (repeat loop)
   - If status="complete": Exit coding loop, proceed to integration phase
   - If status="user_input": Handle user feedback (see User Input Handling), then go to step 1
7. Maximum 5 iterations enforced by MCP
```

**User Input Handling Flow:**

When MCP returns status="user_input" (stagnation detected):

```text
1. Main Agent saves current state to platform:
   - Planning loop: Save BuildPlan via platform tools (Linear/GitHub/Markdown)
   - Coding loop: Ensure latest code committed (should already be done by build_coder)

2. Main Agent retrieves critic feedback via mcp__specter__get_critic_feedback(loop_id)

3. Main Agent presents to user:
   - Current state recap (iteration count, current score, previous score)
   - Challenges faced (extracted from critic feedback)
   - Options for proceeding with pros/cons for each
   - Recommendation for best option

4. User discusses and provides:
   - Selected option
   - Additional feedback/guidance

5. Main Agent stores user feedback via mcp__specter__store_user_feedback(loop_id, feedback_markdown)

6. Loop continues - next agent invocation will retrieve user feedback autonomously
```

---

## Implementation Priority

### Priority 1: Blocking (Cannot Execute Without)

1. ✅ **Create user_feedback_tools.py**
   - `store_user_feedback(loop_id, feedback_markdown)`
   - `get_user_feedback(loop_id)`
   - Register in tool_discovery.py

2. ✅ **Create build_planner.py agent**
   - Tools: get_spec, get_build_plan, get_critic_feedback, get_user_feedback, store_build_plan, Read
   - Instructions: TDD planning, research reference, feedback incorporation

3. ✅ **Create build_critic.py agent**
   - Tools: get_build_plan, get_spec, get_critic_feedback, store_critic_feedback
   - Instructions: FSDD assessment, 80% threshold, progress tracking

4. ✅ **Create build_coder.py agent**
   - Tools: get_build_plan, get_spec, get_critic_feedback, get_user_feedback, Write, Edit, Read, Glob, Bash, TodoWrite, platform tools
   - Instructions: TDD enforcement, TodoList usage, commit strategy

5. ✅ **Create build_reviewer.py agent**
   - Tools: get_build_plan, get_spec, get_critic_feedback, store_critic_feedback, Read, Glob, Bash
   - Instructions: 95% threshold criteria, regression detection

6. ✅ **Update build_command.py**
   - Parallel research execution (single message, multiple Tasks)
   - Planning loop orchestration
   - Coding loop orchestration
   - User input handling
   - Platform integration updates
   - TechnicalSpec status update

### Priority 2: High Impact

1. ✅ **Research requirements extraction logic**
   - Parse TechnicalSpec `research_requirements` field
   - Extract list items (bulleted or numbered)
   - Create research queries

2. ✅ **Platform integration consistency**
   - Uniform update logic across Linear, GitHub, Markdown
   - Implementation summary format

3. ✅ **Git commit strategy in build_coder**
   - Commit after each iteration
   - Proper commit message format
   - Error handling for git operations

4. ✅ **User feedback presentation format**
    - State recap template
    - Options with pros/cons template
    - Recommendation template

### Priority 3: Quality Improvements

1. **95% threshold monitoring**
    - Track stagnation frequency
    - Consider adjustment if needed (90%?)

2. **BuildPlan structure review**
    - Validate against actual implementation needs
    - Update if gaps identified

3. **CriticFeedback structure standardization**
    - Consistent format across build_critic and build_reviewer
    - Machine-parseable if needed

---

## Architectural Decisions (RESOLVED)

### 1. BuildPlan Linking Strategy ✅
**Decision**: Pass `planning_loop_id` to build_coder and build_reviewer agents. They retrieve BuildPlan using this ID from MCP.

### 2. Feedback Passing Mechanism ✅
**Decision**: Agents retrieve all feedback from MCP autonomously using loop_id. Main Agent doesn't pass feedback content (only IDs).

### 3. User Feedback Storage ✅
**Decision**: Add new MCP tools `store_user_feedback` and `get_user_feedback` (similar to critic feedback tools).

### 4. Git Commit Strategy ✅
**Decision**: Commit after each coding iteration for rollback capability and state tracking. Format: `build iteration [N]: [summary]`

### 5. Research Extraction ✅
**Decision**: Extract research items from TechnicalSpec `research_requirements` field. Parse markdown list into individual queries.

### 6. Parallel Research Execution ✅
**Decision**: Single message with multiple Task calls (one per research item). Research-synthesizer agents run concurrently.

### 7. Metadata Capture ✅
**Decision**: Update `spec_status` to IMPLEMENTED. Optionally add `build_planning_score` and `build_coding_score` fields. Do NOT increment `iteration` field.

### 8. Main Agent Role ✅
**Decision**: Pure orchestrator. Receives MCP decisions and acts on them. No thinking, just routing. Maintains minimal state (loop IDs only).

### 9. Agent Autonomy ✅
**Decision**: All agents retrieve documents from MCP autonomously. Main Agent passes only identifiers (loop IDs, project_id, spec_name), never content.

---

## Testing Strategy

### Unit Tests
- User feedback tools (store, retrieve)
- Research requirements extraction logic
- Platform integration update logic

### Integration Tests
- Planning loop (build_planner ↔ build_critic)
- Coding loop (build_coder ↔ build_reviewer)
- User feedback handling flow
- Platform updates (Linear, GitHub, Markdown)

### End-to-End Tests
- Complete /specter-build workflow from command to completion
- User input scenarios (planning stagnation, coding stagnation)
- Multiple research items (parallel execution)
- All three platforms (Linear, GitHub, Markdown)

---

## Success Criteria

### Workflow Execution
- ✅ User can invoke `/specter-build [spec_name]`
- ✅ Research synthesis executes in parallel
- ✅ Planning loop refines to 80% quality
- ✅ Coding loop refines to 95% quality
- ✅ User input handling works for stagnation
- ✅ Platform integration updates correctly
- ✅ TechnicalSpec status updated to IMPLEMENTED

### Code Quality
- ✅ All tests passing (444+ tests)
- ✅ MyPy clean (no type errors)
- ✅ Ruff clean (no linting errors)
- ✅ TDD methodology followed (tests before implementation)
- ✅ Git commits after each iteration

### Agent Behavior
- ✅ Agents retrieve documents autonomously from MCP
- ✅ Main Agent maintains minimal state (loop IDs only)
- ✅ Agents follow retrieve → process → store → exit pattern
- ✅ User feedback incorporated in refinement iterations

### Performance
- ✅ Parallel research execution reduces latency
- ✅ Context usage minimized (agents retrieve, not Main Agent)
- ✅ Stagnation detection prevents infinite loops

---

## Risk Mitigation

### Risk 1: 95% Threshold Unreachable
**Mitigation**: Monitor stagnation frequency. If excessive, lower to 90% or add "good enough" escape hatch after 3 stagnation cycles.

### Risk 2: Research Extraction Fragility
**Mitigation**: Support multiple markdown list formats (bullets, numbers, headings). Add validation and error handling.

### Risk 3: Platform Integration Failures
**Mitigation**: Add error handling for API failures. Provide fallback (log warning, continue workflow).

### Risk 4: Git Commit Failures
**Mitigation**: Handle git errors gracefully (dirty working directory, conflicts). Provide clear error messages to user.

### Risk 5: Agent Deviation from Instructions
**Mitigation**: Clear, explicit agent instructions. Critic feedback keeps agents on course. User input as safety net.

---

## Next Steps

1. Create user_feedback_tools.py (Priority 1.1)
2. Create build_planner.py agent (Priority 1.2)
3. Create build_critic.py agent (Priority 1.3)
4. Create build_coder.py agent (Priority 1.4)
5. Create build_reviewer.py agent (Priority 1.5)
6. Update build_command.py (Priority 1.6)
7. Implement research extraction logic (Priority 2.7)
8. Add platform integration (Priority 2.8)
9. Add git commit strategy (Priority 2.9)
10. Write comprehensive tests

---

## Appendix: File Locations

### Existing Files (Reference)
- [services/models/build_plan.py](services/models/build_plan.py) - BuildPlan model
- [services/models/spec.py](services/models/spec.py) - TechnicalSpec model
- [services/mcp/tools/build_plan_tools.py](services/mcp/tools/build_plan_tools.py) - BuildPlan MCP tools
- [services/templates/commands/build_command.py](services/templates/commands/build_command.py) - Main command
- [docs/commands/specter-build.md](docs/commands/specter-build.md) - Command specification
- [docs/WORKFLOW_REFACTORING_LESSONS.md](docs/WORKFLOW_REFACTORING_LESSONS.md) - Design patterns

### Files to Create
- `services/mcp/tools/user_feedback_tools.py` - User feedback storage

**Agent Templates** (with dual tool architecture):
- `services/templates/agents/build_planner.py` - Planning agent (function: `generate_build_planner_template()`)
- `services/templates/agents/build_critic.py` - Plan critique agent (function: `generate_build_critic_template()`)
- `services/templates/agents/build_coder.py` - TDD implementation agent (function: `generate_build_coder_template(tools: BuildCoderAgentTools)`)
- `services/templates/agents/build_reviewer.py` - Code review agent (function: `generate_build_reviewer_template()`)

### Files to Update
- `services/platform/models.py` - Add `BuildCoderAgentTools` model for platform-specific tool injection
- `services/templates/commands/build_command.py` - Add workflow logic
- `services/platform/tool_discovery.py` - Register user_feedback_tools

---

**End of Implementation Plan**
