from src.platform.models import TaskCommandTools


def generate_task_command_template(tools: TaskCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase-name]
description: Transform Phases into detailed Tasks with implementation Steps through quality-driven refinement
---

# /respec-task Command: Task Orchestration

## Overview
Orchestrate transformation of Phase architecture into a detailed, implementable Task with inline Steps. Bridge architectural design to code implementation through quality-driven task planning.

{tools.mcp_tools_reference}

## Workflow Steps

### 0. Setup and Initialization

#### Step 0.1: Extract Command Arguments and Locate Phase File

Parse command arguments and locate phase file using partial name:

##### Step 0.1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the plan name]
PHASE_NAME_PARTIAL = [second argument from command - partial phase name]
```

##### Step 0.1.2: Search file system for matching phase files

```text
{tools.phase_discovery_instructions}
```

##### Step 0.1.3: Handle multiple matches

```text
IF count(PHASE_FILE_MATCHES) == 0:
  ERROR: "No Phase files found matching '{{PHASE_NAME_PARTIAL}}' in plan {{PLAN_NAME}}"
  SUGGEST: "Verify the phase name or check {tools.phase_location_hint}"
  EXIT: Workflow terminated

ELIF count(PHASE_FILE_MATCHES) == 1:
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
      ... for all matches
    ]

  PHASE_FILE_PATH = [selected file path from AskUserQuestion response]
```

##### Step 0.1.4: Extract canonical name from file path

```text
PHASE_NAME = [basename of PHASE_FILE_PATH without .md extension]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-1")
- PHASE_NAME is the canonical name extracted from file path (e.g., "phase-1-foundation-and-infrastructure")
- Use PHASE_NAME for all MCP storage operations

### 1. Load and Store Phase to MCP

Sync platform phase file to MCP to capture any manual edits:

```text
{tools.sync_phase_instructions}
```

### 2. Extract Research Documentation Paths from Phase

The Phase document contains a "Research Requirements" section with file paths to best-practice documentation.

#### Step 2.1: Parse Phase Research Requirements Section

```text
DOCUMENTATION_PATHS = []

Search PHASE_MARKDOWN for "### Research Requirements" section
IF section exists:
  Extract all file paths matching pattern: `.best-practices/*.md`

  For each path found:
    DOCUMENTATION_PATHS.append(path)
    Display to user: "📚 Research document: {{path}}"

IF DOCUMENTATION_PATHS is empty:
  Display to user: "ℹ️ No research documentation referenced in Phase"
ELSE:
  Display to user: "✓ Found {{len(DOCUMENTATION_PATHS)}} research document(s) to guide task planning"
```

### 3. Initialize Task Planning Loop

Set up MCP-managed quality refinement loop:
{tools.initialize_refinement_loop_inline_doc}
```text
TASK_LOOP_ID = {tools.initialize_loop}
```

### 3.1. Link Loop to Phase

Link the task loop to the phase for agent retrieval:
{tools.link_loop_to_document_inline_doc}
```text
{tools.link_loop}
```

### 4. Task Planning Loop

Coordinate task-planner → task-plan-critic → MCP decision cycle:

#### Step 4.1: Invoke Task-Planner Agent

Use the Task tool to launch the respec-task-planner agent:

```text
Invoke the respec-task-planner agent to generate Task document.

Pass the following information to the agent:
- task_loop_id: TASK_LOOP_ID
- plan_name: PLAN_NAME
- phase_name: PHASE_NAME
- research_file_paths: DOCUMENTATION_PATHS (from Step 2, or empty list)

The agent will:
1. Retrieve Phase from MCP
2. Retrieve previous feedback from MCP (if iteration > 1)
3. Read research briefs from DOCUMENTATION_PATHS (if provided)
4. Generate Task with inline Steps based on Phase and feedback
5. Store Task to MCP

Wait for agent completion before proceeding.
```

Expected: Task document with:
- Goal and Acceptance Criteria from Phase objectives
- Technology Stack Reference from Phase
- Implementation Steps (`#### Step N:` sections, typically 3-6)
- Testing Strategy
- Task naming following `task-N` pattern (matching phase number)

#### Step 4.2: Invoke Task-Plan-Critic Agent

Use the Task tool to launch the respec-task-plan-critic agent:

```text
Invoke the respec-task-plan-critic agent to evaluate Task quality.

Pass the following information to the agent:
- task_loop_id: TASK_LOOP_ID
- plan_name: PLAN_NAME
- phase_name: PHASE_NAME

The agent will:
1. Retrieve Task from MCP
2. Retrieve Phase from MCP
3. Evaluate against FSDD criteria (100-point scale)
4. Store feedback in MCP

Wait for agent completion before proceeding.
```

#### Step 4.3: Get Loop Decision

```text
LOOP_DECISION_RESPONSE = {tools.decide_loop_action}
LOOP_DECISION = LOOP_DECISION_RESPONSE.status
LOOP_SCORE = LOOP_DECISION_RESPONSE.current_score
LOOP_ITERATION = LOOP_DECISION_RESPONSE.iteration

Decision options: "complete", "refine", "user_input"
```

### 5. MCP Decision Handling

**Follow LOOP_DECISION exactly. Do not override based on score assessment.**

```text
IF LOOP_DECISION == "refine":
  Display: "⟳ Iteration {{LOOP_ITERATION}} · Score: {{LOOP_SCORE}}/100 — refining task"
  Return to Step 4.1 (task-planner will retrieve feedback from MCP itself)

ELIF LOOP_DECISION == "user_input":
  Display: "⚠ Quality improvements needed - user input required"

  (ONLY NOW retrieve feedback for user display)
  LATEST_FEEDBACK = {tools.get_feedback}

  Display LATEST_FEEDBACK to user with:
  - Current score and iteration
  - Key issues identified by task-plan-critic
  - Recommendations for improvement

  Use AskUserQuestion tool to present options:
  Question: "The Task quality is at [SCORE]/100. How would you like to proceed?"
  Options:
    1. "Proceed with current Task - quality is sufficient"
    2. "One more refinement iteration - address remaining issues"
    3. "Provide specific guidance for refinement"

  IF user selects option 1:
    Override MCP decision and proceed to Step 6
  ELIF user selects option 2:
    Return to Step 4.1 for one more refinement iteration
  ELIF user selects option 3:
    Prompt for specific guidance
    Store as user feedback using store_user_feedback
    Return to Step 4.1 with user guidance

ELIF LOOP_DECISION == "complete":
  Display: "✅ Score: {{LOOP_SCORE}}/100 — task approved"
  Proceed to Step 6.
```

### 6. Retrieve Final Task

Retrieve the completed Task from MCP:

```text
FINAL_TASK = {tools.get_task}
```

### 7. Store Task to Platform File System

Write Task to platform file for user review and version control:

```text
TASK_NAME = PHASE_NAME.replace("phase-", "task-")
# Example: phase-1-foundation-and-infrastructure → task-1-foundation-and-infrastructure

TASK_FILE_PATH = {tools.task_resource_pattern}

Ensure directory exists:
{tools.task_location_setup}

Write FINAL_TASK to TASK_FILE_PATH

Display to user: "✓ Task saved to: {{TASK_FILE_PATH}}"
```

### 8. Final Reporting

Present completion summary with clear next steps:

```text
**Task Created Successfully**:
- Quality Score: [score from final iteration]
- Total Iterations: [iteration count]
- Task Name: {{TASK_NAME}}

**Storage Locations**:
- MCP: {{PLAN_NAME}}/{{PHASE_NAME}}/{{TASK_NAME}}
- Platform File: {{TASK_FILE_PATH}}

**Task Summary**:
- **Goal**: [Goal from Task]
- **Checklist Items**: [Number of items in Checklist]
- **Steps**: [Number of Steps in Task]
- **Testing Strategy**: [Brief testing description]

**Readiness Assessment**:
✅ Task ready for implementation
✅ Implementation Checklist defined with verification methods
✅ Implementation Steps defined
✅ Testing strategy documented
✅ Technology stack aligned with Phase

**Next Steps**:
Execute /respec-code {{PLAN_NAME}} {{PHASE_NAME}} to implement the Task with TDD
```

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No phase found for: [PLAN_NAME]/[PHASE_NAME]"
Suggest: "/respec-phase [PLAN_NAME] [PHASE_NAME] to create phase"
Exit gracefully with guidance
```

#### Agent Failures
```text
IF task-planner fails:
  Retry once with simplified input
  If still fails, provide manual task template
  Note limitations in output

IF task-plan-critic fails:
  Continue without quality loop
  Proceed with single-pass task generation
  Note manual review recommended
```

#### MCP Loop Failures
```text
IF loop initialization fails:
  Continue with single-pass task generation
  Skip refinement cycles
  Note quality assessment unavailable
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Validating Phase completion** before proceeding
- **Extracting research documentation paths** from Phase
- **Managing task planning loop** without defining agent behavior
- **Handling MCP Server responses** without evaluating quality scores
- **Storing artifacts** to both MCP and platform file system
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **respec-task-planner**: Task generation with inline Steps
- **respec-task-plan-critic**: Quality assessment against FSDD criteria
- **MCP Server**: Decision logic and threshold management

Ready for code implementation through /respec-code command execution with validated Task.
"""
