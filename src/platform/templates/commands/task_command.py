from src.platform.models import TaskCommandTools


def generate_task_command_template(tools: TaskCommandTools) -> str:
    selection_prompt_instructions = tools.tui_adapter.selection_prompt_instruction
    selection_response_source = tools.tui_adapter.selection_response_source
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase request]
description: Transform Phases into detailed Tasks with implementation Steps through quality-driven refinement
---

# respec-task Command: Task Orchestration

## Overview
Orchestrate transformation of Phase architecture into a detailed, implementable Task with inline Steps. Bridge architectural design to code implementation through quality-driven task planning.

{tools.mcp_tools_reference}

{tools.tui_adapter.subagent_invocation_guardrail}

## Workflow Steps

### 0. Setup and Initialization

#### Step 0.1: Parse User Inputs and Locate Phase File

Parse user inputs and locate the target phase without guessing at free-form boundaries:

##### Step 0.1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the plan name]
RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]
```

##### Step 0.1.1.a: Initialize workflow variables

```text
PHASE_NAME_PARTIAL = [empty until RAW_PHASE_REQUEST is clarified]
OPTIONAL_CONTEXT = [empty until RAW_PHASE_REQUEST is clarified]
```

Fail closed on ambiguity:
- Treat RAW_PHASE_REQUEST as the only user-authored source of truth after PLAN_NAME.
- Do NOT assume RAW_PHASE_REQUEST has a clean boundary between the phase reference
  and additional task-planning guidance.
- Ask the user a clarifying question or present options whenever multiple reasonable
  interpretations would change the selected phase, task scope, planning direction,
  validation criteria, or what to pass downstream as guidance.
- Do NOT begin phase lookup until the phase reference is sufficiently clear.

Once RAW_PHASE_REQUEST is sufficiently clear:
- PHASE_NAME_PARTIAL = [clarified phase selector derived from RAW_PHASE_REQUEST]
- OPTIONAL_CONTEXT = [remaining clarified task-planning guidance, otherwise empty string]

If OPTIONAL_CONTEXT is present after clarification, preserve it for the full
task-planning loop and pass it through to the task-planner and task-plan-critic agents.

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
  {selection_prompt_instructions}
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

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 0.1.3. Set PHASE_FILE_PATH. Continue to Step 0.1.4 immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  PHASE_FILE_PATH = [selected file path from {selection_response_source}]
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

═══════════════════════════════════════════════
MANDATORY RESEARCH EXTRACTION PROTOCOL
═══════════════════════════════════════════════
```text
DOCUMENTATION_PATHS = []

Search PHASE_MARKDOWN for "### Research Requirements" section

IF section NOT found:
  DOCUMENTATION_PATHS = []
  Display: "ℹ️ No Research Requirements section found in Phase"

IF section found:
  Extract all file paths matching pattern: `.best-practices/*.md`

  For each path found:
    DOCUMENTATION_PATHS.append(path)
    Display: "📚 Research document: {{path}}"

  IF no paths found after scanning entire section:
    Display: "⚠️ Research Requirements section exists but contains no valid paths"
    DOCUMENTATION_PATHS = []

IF DOCUMENTATION_PATHS is non-empty:
  Display: "✓ Found {{len(DOCUMENTATION_PATHS)}} research document(s) to guide task planning"
```

Do NOT silently treat "section exists with no paths" as equivalent to "section missing".
═══════════════════════════════════════════════

#### Step 2.2: Parse Implementation Plan References

```text
IMPL_PLAN_PATHS = []
IMPL_PLAN_REFERENCES = []

Search PHASE_MARKDOWN for "### Implementation Plan References" section:
  IF section found:
    For each line matching "- Constraint: `<path>`":
      Extract:
        - PATH from backtick-quoted value
        - SECTION (optional) from `§ "Section Name"` if present
        - LINE_RANGE (optional) from `(lines X-Y)` if present

      Append PATH to IMPL_PLAN_PATHS (if not already present)
      Append structured reference to IMPL_PLAN_REFERENCES:
        {{
          "path": PATH,
          "section": SECTION or None,
          "line_range": LINE_RANGE or None
        }}
      Display to user: "📌 Implementation constraint: {{PATH}} {{SECTION}} {{LINE_RANGE}}"

Also scan full PHASE_MARKDOWN for "→ before implementing, read" directives (backward compat):
  For each directive found:
    Extract file_path from backtick-quoted value after "read"
    IF path not already in IMPL_PLAN_PATHS:
      IMPL_PLAN_PATHS.append(path)
      IMPL_PLAN_REFERENCES.append({{"path": path, "section": None, "line_range": None}})
      Display to user: "📌 Implementation constraint (inline): {{path}}"

IF IMPL_PLAN_PATHS is empty:
  Display to user: "ℹ️ No implementation plan references in Phase"
ELSE:
  Display to user: "✓ Found {{len(IMPL_PLAN_PATHS)}} implementation constraint(s)"
  Display to user: "✓ Structured citations available: {{len(IMPL_PLAN_REFERENCES)}}"
```

#### Step 2.25: Constraint Precedence Contract

```text
Task planning MUST apply this precedence order:
1. `TUI Plan Deviation Log` entries in Phase (if present)
2. Remaining implementation plan references (IMPL_PLAN_REFERENCES)
3. Research documentation paths (DOCUMENTATION_PATHS)

WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:
  ## Workflow Guidance
  ### Guidance Summary
  [OPTIONAL_CONTEXT if present, otherwise "None"]
  ### Constraints
  - [preserved constraint from OPTIONAL_CONTEXT]
  - None
  ### Resume Context
  - [resume detail from OPTIONAL_CONTEXT]
  - None
  ### Settled Decisions
  - [clarified decision from OPTIONAL_CONTEXT]
  - None

REFERENCE_CONTEXT_MARKDOWN = compose markdown:
  ## Reference Context
  ### Research File Paths
  - [each path from DOCUMENTATION_PATHS]
  - None
  ### Implementation Plan Paths
  - [each path from IMPL_PLAN_PATHS]
  - None
  ### Structured References
  - path: [reference.path]
    section: [reference.section or "None"]
    line_range: [reference.line_range or "None"]
  - None

Pass REFERENCE_CONTEXT_MARKDOWN and WORKFLOW_GUIDANCE_MARKDOWN to task-planner.
```

#### Step 2.3: Fail Fast on Unresolved Synthesize Prompts

```text
SYNTHESIZE_PROMPTS = []

Search PHASE_MARKDOWN for lines matching:
  "- Synthesize: <prompt text>"

For each match:
  SYNTHESIZE_PROMPTS.append(prompt text)

IF SYNTHESIZE_PROMPTS is non-empty:
  ERROR: "Phase contains unresolved research synthesis prompts"
  Display:
  - "Unresolved Synthesize prompts: {{len(SYNTHESIZE_PROMPTS)}}"
  - "Task planning is blocked until phase-owned synthesis is complete."

  REQUIRED ACTION:
  - Re-run phase workflow for this phase so Step 7.5 converts Synthesize prompts to Read paths:
    {tools.phase_command_invocation}

  FAIL-CLOSED:
  - Do NOT invoke task-planner
  - Do NOT continue to Step 3
  - Exit with diagnostics and retry guidance
```

{tools.task_command_reference} consumes finalized research artifacts only. It MUST NOT execute bp synthesis itself.

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

Invoke the task-planner workflow:

{tools.invoke_task_planner}

```text
IF task-planner reports failure:
  ERROR: "Task planner failed"
  DIAGNOSTIC: [surface the exact planner error/output]
  FAIL-CLOSED:
  - Do NOT invoke task-plan-critic
  - Do NOT continue to Step 4.3
  EXIT: Workflow terminated

IF task-planner does NOT confirm "Task stored and verified.":
  ERROR: "Task planner did not confirm current-pass Task storage"
  DIAGNOSTIC: [surface the exact planner output]
  FAIL-CLOSED:
  - Do NOT invoke task-plan-critic
  - Do NOT continue to Step 4.3
  EXIT: Workflow terminated

TASK_MARKDOWN = {tools.get_task}

IF TASK_MARKDOWN not found or retrieval fails:
  ERROR: "Task planner did not produce a retrievable Task document"
  DIAGNOSTIC: [surface the exact retrieval error/output]
  FAIL-CLOSED:
  - Do NOT invoke task-plan-critic
  - Do NOT continue to Step 4.3
  EXIT: Workflow terminated
```

#### Step 4.2: Invoke Task-Plan-Critic Agent

```text
PRE_TASK_LOOP_STATUS = {tools.get_loop_status}
```

Invoke the task-plan-critic workflow:

{tools.invoke_task_plan_critic}

```text
IF task-plan-critic reports failure:
  ERROR: "Task plan critic failed"
  DIAGNOSTIC: [surface the exact critic error/output]
  FAIL-CLOSED:
  - Do NOT call decide_loop_action
  - Do NOT continue to Step 5
  EXIT: Workflow terminated

POST_TASK_LOOP_STATUS = {tools.get_loop_status}
TASK_FEEDBACK = {tools.get_feedback}

IF TASK_FEEDBACK is empty OR retrieval fails:
  ERROR: "Task plan critic did not persist CriticFeedback"
  DIAGNOSTIC: [surface the exact MCP/tool error]
  FAIL-CLOSED:
  - Do NOT call decide_loop_action
  - Do NOT continue to Step 5
  EXIT: Workflow terminated

IF PRE_TASK_LOOP_STATUS.status == "initialized" AND POST_TASK_LOOP_STATUS.status == "initialized":
  ERROR: "Task plan critic did not advance loop state"
  DIAGNOSTIC: [surface PRE_TASK_LOOP_STATUS and POST_TASK_LOOP_STATUS]
  FAIL-CLOSED:
  - Do NOT call decide_loop_action
  - Do NOT continue to Step 5
  EXIT: Workflow terminated

IF PRE_TASK_LOOP_STATUS.status != "initialized" AND POST_TASK_LOOP_STATUS.iteration <= PRE_TASK_LOOP_STATUS.iteration:
  ERROR: "Task plan critic did not persist fresh loop feedback"
  DIAGNOSTIC: [surface PRE_TASK_LOOP_STATUS and POST_TASK_LOOP_STATUS]
  FAIL-CLOSED:
  - Do NOT call decide_loop_action
  - Do NOT continue to Step 5
  EXIT: Workflow terminated
```

#### Step 4.3: Get Loop Decision

```text
LOOP_DECISION_RESPONSE = {tools.decide_loop_action}
LOOP_DECISION = LOOP_DECISION_RESPONSE.status
LOOP_SCORE = LOOP_DECISION_RESPONSE.current_score
LOOP_ITERATION = LOOP_DECISION_RESPONSE.iteration

Decision options: "completed", "refine", "user_input"
```

### 5. MCP Decision Handling

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
IF LOOP_DECISION == "refine":
  Display: "⟳ Iteration {{LOOP_ITERATION}} · Score: {{LOOP_SCORE}}/100 — refining task"
  Return to Step 4.1 (task-planner → Task retrieval verification → task-plan-critic → feedback verification → decision)

ELIF LOOP_DECISION == "user_input":
  Display: "⚠ Quality improvements needed - user input required"

  (ONLY NOW retrieve feedback for user display)
  LATEST_FEEDBACK = {tools.get_feedback}

  Display LATEST_FEEDBACK to user with:
  - Current score and iteration
  - Key issues identified by task-plan-critic
  - Recommendations for improvement

  ═══════════════════════════════════════════════
  MANDATORY USER INPUT PROTOCOL
  ═══════════════════════════════════════════════
  User provides FEEDBACK only. The MCP Server controls the
  refine/complete decision after receiving user input.

  Do NOT let user override MCP decision.
  Do NOT proceed to Step 6 based on user choice alone.

  VIOLATION: "User said proceed, so I'll skip refinement"
             is a workflow violation. MCP decides, not user.
  ═══════════════════════════════════════════════

  {selection_prompt_instructions}
  Question: "The Task quality is at [SCORE]/100. How would you like to proceed?"
  Options:
    1. "Proceed with current Task - quality is sufficient"
    2. "One more refinement iteration - address remaining issues"
    3. "Provide specific guidance for refinement"

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 5. Capture the selected guidance path. Continue with feedback storage immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF user selects option 1:
    Store user feedback: "User confirmed current quality is acceptable"
  ELIF user selects option 2:
    Store user feedback: "User requested one more refinement iteration"
  ELIF user selects option 3:
    Prompt for specific guidance
    Store user feedback with guidance

  Return to Step 4.1 (task-planner → Task retrieval verification → task-plan-critic → feedback verification → decision)

ELIF LOOP_DECISION == "completed":
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
═══════════════════════════════════════════════
MANDATORY TASK IDENTITY EXTRACTION PROTOCOL
═══════════════════════════════════════════════
Parse FINAL_TASK as Task markdown.
TASK_NAME = [extract the H1 title value after "# Task:" from FINAL_TASK]

IF TASK_NAME is empty OR extraction fails:
  ERROR: "Final Task document is missing a usable task name"
  DIAGNOSTIC: [surface parse/extraction failure]
  EXIT with error message

Display: "✓ Task name: {{TASK_NAME}}"
═══════════════════════════════════════════════

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
Use the implementation workflow to implement the Task with TDD:
{tools.code_command_invocation}
```

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No phase found for: [PLAN_NAME]/[PHASE_NAME]"
Suggest: "Use phase workflow to create phase"
{tools.phase_command_invocation}
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

Ready for code implementation through the implementation workflow with validated Task.
"""
