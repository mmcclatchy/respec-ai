from src.platform.models import PlanRoadmapCommandTools


def generate_roadmap_command_template(tools: PlanRoadmapCommandTools) -> str:
    selection_prompt_instructions = tools.tui_adapter.selection_prompt_instruction
    selection_response_source = tools.tui_adapter.selection_response_source
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [optional: roadmap-guidance]
description: Transform strategic plans into multiple Phases through quality-driven refinement
---

# respec-roadmap Command: Implementation Roadmap Orchestration

## Overview
Orchestrate the transformation of strategic plans into discrete, implementable phase roadmaps. Bridge strategic planning to Phase creation through quality-driven decomposition and refinement.

{tools.mcp_tools_reference}

{tools.tui_adapter.subagent_invocation_guardrail}

## Workflow Steps

### 0. Setup and Initialization

#### Step 0.1: Extract Command Arguments

Parse command arguments from user input:
```text
PLAN_NAME = [first argument from command - the project name]
RAW_PHASING_REQUEST = [all remaining input after PLAN_NAME]
PHASING_PREFERENCES = [normalized roadmap-guidance brief derived from RAW_PHASING_REQUEST, or empty string]
```

**Important**: PLAN_NAME from command arguments is used for all MCP storage operations.

Interpret trailing roadmap guidance as one payload:
- Treat RAW_PHASING_REQUEST as the only user-authored roadmap guidance after PLAN_NAME.
- Normalize guidance into PHASING_PREFERENCES or leave it empty.
- If ambiguity materially changes roadmap structure, {selection_prompt_instructions} or ask one direct clarification question. WAIT for {selection_response_source}. DO NOT treat this as workflow completion, cancellation, or failure. After the user responds, resume at Step 0.1. Update PHASING_PREFERENCES. Continue to Step 0.2 immediately. DO NOT explain that the workflow is stopping unless the user asks why.
#### Step 0.2: Sync Plan from Platform to MCP

**CRITICAL**: Sync the plan from platform storage to MCP before proceeding. This ensures any manual edits the user made to the plan file are captured.

```text
{tools.sync_plan_instructions}
```

### 1. Strategic Plan Retrieval and Validation
Retrieve and validate the synced strategic plan:

#### Retrieve Plan
```text
STRATEGIC_PLAN = {tools.get_plan}
IF STRATEGIC_PLAN not found:
  ERROR: "No strategic plan found for project: [PLAN_NAME]"
  SUGGEST: "Use the strategic planning workflow to create the plan first"
  {tools.plan_command_invocation}
  EXIT: Graceful failure with guidance
STRUCTURED_OBJECTIVES = [Extract from strategic plan Business Objectives analysis]
```

#### Validate Plan Constraint Sections
```text
PLAN_HAS_ARCHITECTURE = STRATEGIC_PLAN contains "## Architecture Direction" section
PLAN_HAS_TECH_DECISIONS = STRATEGIC_PLAN contains "### Chosen Technologies" section
PLAN_HAS_ANTI_REQUIREMENTS = STRATEGIC_PLAN contains "### Anti-Requirements" section
PLAN_HAS_QUALITY_BAR = STRATEGIC_PLAN contains "### Quality Bar" section
CONSTRAINT_SECTIONS_FOUND = count of True values above

IF CONSTRAINT_SECTIONS_FOUND == 0:
  Display: "⚠️ Plan has no constraint sections (Architecture Direction, Technology Decisions, Anti-Requirements, Quality Bar)"
  Display: "Roadmap will proceed without plan constraint guidance"
  Display: "Use the strategic planning workflow to add these sections for better phase quality"
  Display: "{tools.plan_command_invocation}"
ELSE:
  Display: "✓ Found {{CONSTRAINT_SECTIONS_FOUND}}/4 plan constraint sections"
  IF not PLAN_HAS_ARCHITECTURE: Display: "  ⚠️ Missing: Architecture Direction"
  IF not PLAN_HAS_TECH_DECISIONS: Display: "  ⚠️ Missing: Technology Decisions"
  IF not PLAN_HAS_ANTI_REQUIREMENTS: Display: "  ⚠️ Missing: Anti-Requirements"
  IF not PLAN_HAS_QUALITY_BAR: Display: "  ⚠️ Missing: Quality Bar"
```

### 2. Initialize Roadmap Generation Loop
Set up MCP-managed quality refinement loop:
{tools.initialize_refinement_loop_inline_doc}
```text
ROADMAP_LOOP_ID = {tools.initialize_loop})
```

### 3. Roadmap Generation Loop
Coordinate roadmap → roadmap-critic → MCP decision cycle:

#### Step 3.1: Invoke Roadmap Agent

Invoke the roadmap workflow with these instructions:

{tools.invoke_roadmap_agent}

```text
IF roadmap agent reports failure:
  ERROR: "Roadmap agent failed" DIAGNOSTIC: [surface the exact roadmap-agent error/output]
  FAIL-CLOSED: Do NOT invoke roadmap-critic. Do NOT continue to Step 3.3. EXIT: Workflow terminated

IF roadmap agent does NOT confirm "Roadmap generation complete. Stored to MCP.":
  ERROR: "Roadmap agent did not confirm current-pass roadmap storage" DIAGNOSTIC: [surface the exact roadmap-agent output]
  FAIL-CLOSED: Do NOT invoke roadmap-critic. Do NOT continue to Step 3.3. EXIT: Workflow terminated

ROADMAP_MARKDOWN = {tools.get_roadmap}

IF ROADMAP_MARKDOWN not found or retrieval fails:
  ERROR: "Roadmap agent did not produce a retrievable roadmap" DIAGNOSTIC: [surface the exact retrieval error/output]
  FAIL-CLOSED: Do NOT invoke roadmap-critic. Do NOT continue to Step 3.3. EXIT: Workflow terminated
```

Implementation roadmap requirements: feature-based where useful, technically coherent, incremental-complexity aware, risk-based, independently testable, meaningfully scoped, and dependency-ordered.

#### Step 3.2: Invoke Roadmap-Critic Agent
```text
PRE_ROADMAP_LOOP_STATUS = {tools.get_loop_status}
```

Invoke the roadmap-critic workflow with these instructions:

{tools.invoke_roadmap_critic}

```text
IF roadmap-critic reports failure:
  ERROR: "Roadmap critic failed" DIAGNOSTIC: [surface the exact critic error/output]
  FAIL-CLOSED: Do NOT call decide_loop_action. Do NOT continue to Step 4. EXIT: Workflow terminated

POST_ROADMAP_LOOP_STATUS = {tools.get_loop_status}
ROADMAP_FEEDBACK = {tools.get_feedback}

IF ROADMAP_FEEDBACK is empty OR retrieval fails:
  ERROR: "Roadmap critic did not persist CriticFeedback" DIAGNOSTIC: [surface the exact MCP/tool error]
  FAIL-CLOSED: Do NOT call decide_loop_action. Do NOT continue to Step 4. EXIT: Workflow terminated

IF PRE_ROADMAP_LOOP_STATUS.status == "initialized" AND POST_ROADMAP_LOOP_STATUS.status == "initialized":
  ERROR: "Roadmap critic did not advance loop state" DIAGNOSTIC: [surface PRE_ROADMAP_LOOP_STATUS and POST_ROADMAP_LOOP_STATUS]
  FAIL-CLOSED: Do NOT call decide_loop_action. Do NOT continue to Step 4. EXIT: Workflow terminated

IF PRE_ROADMAP_LOOP_STATUS.status != "initialized" AND POST_ROADMAP_LOOP_STATUS.iteration <= PRE_ROADMAP_LOOP_STATUS.iteration:
  ERROR: "Roadmap critic did not persist fresh loop feedback" DIAGNOSTIC: [surface PRE_ROADMAP_LOOP_STATUS and POST_ROADMAP_LOOP_STATUS]
  FAIL-CLOSED: Do NOT call decide_loop_action. Do NOT continue to Step 4. EXIT: Workflow terminated
```

#### Step 3.3: Get Loop Decision
```text
LOOP_DECISION_RESPONSE = {tools.decide_loop_action}
LOOP_DECISION = LOOP_DECISION_RESPONSE.status
LOOP_SCORE = LOOP_DECISION_RESPONSE.current_score
LOOP_ITERATION = LOOP_DECISION_RESPONSE.iteration

Decision options: "completed", "refine", "user_input"
```

### 4. MCP Decision Handling

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
  Display: "⟳ Iteration {{LOOP_ITERATION}} · Score: {{LOOP_SCORE}}/100 — refining roadmap"
  Return to Step 3.1 (roadmap generation → roadmap retrieval verification → roadmap-critic → feedback verification → decision)

ELIF LOOP_DECISION == "user_input":
  Display: "⚠ Quality improvements needed - user input required"

  LATEST_FEEDBACK = {tools.get_feedback})
  Display LATEST_FEEDBACK to user with current score, iteration, key issues, and recommendations.

  {selection_prompt_instructions}
  Question: "The roadmap quality is at [SCORE]/100. How would you like to proceed?"
  Options:
    1. "Proceed with current roadmap - quality is sufficient"
    2. "One more refinement iteration - address remaining issues"
    3. "Provide specific guidance for refinement"
  WAIT for {selection_response_source}. DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 4. Branch on the selected option. Continue with the matching roadmap action immediately. DO NOT explain that the workflow is stopping unless the user asks why.

  IF user selects option 1:
    Store user feedback: "User confirmed current roadmap direction is acceptable"
    Return to Step 3.1 (MCP will decide the next action after reevaluating stored feedback)
  ELIF user selects option 2:
    Store user feedback: "User requested one more roadmap refinement iteration"
    Return to Step 3.1 (roadmap generation → roadmap retrieval verification → roadmap-critic → feedback verification → decision)
  ELIF user selects option 3:
    Prompt for specific guidance
    Store as user feedback using store_user_feedback
    Return to Step 3.1 (roadmap generation → roadmap retrieval verification → roadmap-critic → feedback verification → decision)

ELIF LOOP_DECISION == "completed":
  Display: "✅ Score: {{LOOP_SCORE}}/100 — roadmap approved · extracting phases..."
  IMMEDIATELY proceed to Step 5. The roadmap is NOT the final output.
```

═══════════════════════════════════════════════
MANDATORY: PHASE EXTRACTION IS NOT OPTIONAL
═══════════════════════════════════════════════
The roadmap is internal MCP working data only.
Do NOT write roadmap files to disk. Do NOT stop here. Do NOT report roadmap completion.
The workflow is NOT complete until Steps 5-7 finish (plan extraction, create phases, verify storage).

VIOLATION: Stopping after the roadmap quality loop without extracting
           phases is a workflow violation. The roadmap exists solely to
           produce Phase documents — it has no value on its own.
═══════════════════════════════════════════════

### 5. Phase Extraction Planning (MANDATORY)
Plan extraction of sparse Phases from roadmap before parallel processing:

#### Retrieve Final Roadmap
```text
FINAL_ROADMAP = {tools.get_roadmap})
Parse FINAL_ROADMAP to extract:
  - ROADMAP_PHASES: List of all phases with names, durations, dependencies
  - PHASE_COUNT: Total number of phases
```

#### Analyze Phase Sizing
```text
For each phase in ROADMAP_PHASES:
  - Validate sprint-appropriate scope (2-4 weeks of work per roadmap design)
  - Identify prerequisite dependencies and proper ordering
  - Determine specific phase responsibilities and technical focus
```

#### Create Phase Extraction Plan
```text
SPEC_EXTRACTION_PLAN = Generate plan for extracting phases from roadmap:
  - Phase ordering based on dependencies
  - One phase per phase (PHASE_COUNT total phases to extract and save)
  - Success criteria: Each extracted phase is sparse (iteration=0) matching roadmap content

**Remember**: Phases already exist in roadmap - we're just extracting and saving them to MCP.
```

### 6. Parallel Phase Extraction (MANDATORY)
Extract sparse Phases from roadmap and save to MCP storage:

**CRITICAL UNDERSTANDING**: The roadmap agent ALREADY CREATED sparse Phase objects (iteration=0) embedded in the roadmap markdown. The create-phase agents DO NOT generate new phases - they extract existing phases from the roadmap and save them to MCP.

#### Launch Parallel Phase Extraction Agents

Launch all create-phase workflows IN PARALLEL:

```text
For each phase in ROADMAP_PHASES, invoke a respec-create-phase agent.

Pass the following information to each agent:
- plan_name: PLAN_NAME
- phase_name: [the specific phase name from ROADMAP_PHASES]
- loop_id: ROADMAP_LOOP_ID

Each agent will:
1. Retrieve roadmap from MCP using get_roadmap
2. Extract the phase matching the provided phase_name
3. Store to MCP using store_document
4. Store to platform using platform-specific tool

Each agent will NOT return the phase markdown.
Each agent will report only: completion status and any errors encountered.

{tools.phase_extraction_parallel_policy}
```

#### Aggregate Results
```text
After all agents complete, collect results:
- SUCCESSFUL_PHASES: List of phases created successfully
- FAILED_PHASES: List of phases that failed with error details
- TOTAL_PHASES: MUST equal PHASE_COUNT

Validate that each planned phase has a corresponding phase result.
```

### 7. Verify Phase Creation (MANDATORY)

**CRITICAL**: Verify actual platform storage, not agent completion messages.

Verification Sequence:
```text
STEP 1: Extract Expected Phase Names from Roadmap
EXPECTED_PHASE_NAMES = [Extract phase names from FINAL_ROADMAP (retrieved in Step 5)]
EXPECTED_COUNT = length of EXPECTED_PHASE_NAMES

STEP 2: Query Platform Storage
STORED_PHASES = {tools.list_project_phases_tool_interpolated}
ACTUAL_COUNT = length of STORED_PHASES

IF ACTUAL_COUNT == 0:
  Display: "❌ Zero phases found in platform storage despite agent completion."
  Display: "Check create-phase agent logs for errors."
  STOP. Do NOT present completion summary. Do NOT suggest next steps.
  Report: "Roadmap command failed — 0 of EXPECTED_COUNT phases stored."

STEP 3: Verification Report
For each phase_name in EXPECTED_PHASE_NAMES:
  IF phase_name in STORED_PHASES:
    STATUS = "✅ SUCCESS"
  ELSE:
    STATUS = "❌ FAILED"
    LOG: Phase not found in platform storage despite agent completion

  Record: (phase_name, status)

STEP 4: Generate Evidence-Based Report
Report actual verification results:
  - Total phases expected: EXPECTED_COUNT
  - Successfully stored: [count with ✅]
  - Failed storage: [count with ❌]
  - Evidence: Platform list response

DO NOT rely on agent completion messages.
Only report success for phases verified in platform storage.
```

### 8. Final Integration and Comprehensive Reporting

Present verified results only:

```text
**Roadmap Completed**:
- Quality Score: [score from Step 3.4]
- Total Phases: [PHASE_COUNT from Step 5]

**Phase Storage Verification** (from Step 7):
- Phases in Platform Storage: [ACTUAL_COUNT] of [EXPECTED_COUNT]
- Verified Phases: [list of ✅ phase names]
- Missing Phases: [list of ❌ phase names]
- Evidence: Platform list response

**Readiness Assessment**:
IF ACTUAL_COUNT == EXPECTED_COUNT:
  ✅ All phases ready for phase development workflow
  Next: Run phase workflow on individual phases
  {tools.phase_command_invocation}
ELSE:
  ⚠️ Partial completion - manual intervention required
  Missing: [list specific phase names without platform storage]
  Action: Review Step 6 agent failures and retry failed phases

**Next Steps**:
[Provide specific guidance based on actual verification results]
```

## Error Handling

### Graceful Degradation Patterns

#### Strategic Plan Not Available
```text
Display: "No strategic plan found for project: [PLAN_NAME]"
Suggest: "Use strategic planning workflow to create strategic plan"
{tools.plan_command_invocation}
Exit gracefully with guidance
```

#### Agent Failures
```text
IF roadmap fails:
  Retry once with simplified input
  Create basic 3-phase roadmap as fallback
  Note limitations in output

IF roadmap-critic fails:
  Continue without quality loop
  Proceed with single-pass roadmap
  Note manual review recommended
```

#### MCP Loop Failures
```text
IF loop initialization fails:
  Continue with single-pass roadmap generation
  Skip refinement cycles
  Note quality assessment unavailable
```

#### Parallel Phase Creation Failures
```text
IF some create-phase agents fail:
  Continue with successful phase creations
  Categorize failures by type:
    - Phase context extraction failures: Provide manual phase template
    - MCP storage failures: Retry storage operation once
    - Complete agent failures: Log error and continue with remaining phases
  Report detailed completion status:
    - Total phases planned: X
    - Successfully created: Y
    - Failed with recovery: Z
    - Failed completely: W
  Provide specific guidance for each failed phase:
    - Manual creation templates for context extraction failures
    - Debugging information for technical issues
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Validating strategic plan completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Handling MCP Server responses** without evaluating quality scores
- **Managing phase planning** before parallel creation
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **roadmap**: Phase breakdown and roadmap generation (with MCP tool access)
- **roadmap-critic**: Quality assessment and feedback
- **create-phase**: Individual InitialPhase extraction and MCP storage
- **MCP Server**: Decision logic and threshold management

## Workflow Enhancements

### Strategic Plan Validation
- Verifies analyst-critic validation completion before roadmap generation
- Provides clear error messages for incomplete plans
- Ensures high-quality input for roadmap planning

### Phase Planning Integration
- Analyzes sprint-appropriate sizing before phase creation
- Coordinates prerequisite ordering and dependencies
- Manages MCP storage for phase tracking

Ready for Phase development through the phase workflow on individual phases with validated input.
"""
