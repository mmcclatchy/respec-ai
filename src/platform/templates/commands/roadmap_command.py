from src.platform.models import PlanRoadmapCommandTools


def generate_roadmap_command_template(tools: PlanRoadmapCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [optional: phasing-preferences]
description: Transform strategic plans into multiple Phases through quality-driven refinement
---

# /respec-roadmap Command: Implementation Roadmap Orchestration

## Overview
Orchestrate the transformation of strategic plans into discrete, implementable phase roadmaps. Bridge strategic planning to Phase creation through quality-driven decomposition and refinement.

{tools.mcp_tools_reference}

## Workflow Steps

### 0. Setup and Initialization

#### Step 0.1: Extract Command Arguments

Parse command arguments from user input:
```text
PLAN_NAME = [first argument from command - the project name]
PHASING_PREFERENCES = [second argument if provided, otherwise empty string]
```

**Important**: PLAN_NAME from command arguments is used for all MCP storage operations.

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
  SUGGEST: "Run '/respec-plan [PLAN_NAME]' to create strategic plan first"
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
  Display: "Roadmap will proceed but phases may lack constraint guidance"
  Display: "Consider running '/respec-plan' to add these sections"
ELSE:
  Display: "✓ Found {{CONSTRAINT_SECTIONS_FOUND}}/4 plan constraint sections"
  IF not PLAN_HAS_ARCHITECTURE: Display: "  ⚠️ Missing: Architecture Direction"
  IF not PLAN_HAS_TECH_DECISIONS: Display: "  ⚠️ Missing: Technology Decisions"
  IF not PLAN_HAS_ANTI_REQUIREMENTS: Display: "  ⚠️ Missing: Anti-Requirements"
  IF not PLAN_HAS_QUALITY_BAR: Display: "  ⚠️ Missing: Quality Bar"
```

Note: PHASING_PREFERENCES already extracted from command arguments in Step 0.1.

### 2. Initialize Roadmap Generation Loop
Set up MCP-managed quality refinement loop:
{tools.initialize_refinement_loop_inline_doc}
```text
ROADMAP_LOOP_ID = {tools.initialize_loop})
```

### 3. Roadmap Generation Loop
Coordinate roadmap → roadmap-critic → MCP decision cycle:

#### Step 3.1: Invoke Roadmap Agent

Use the Task tool to launch the respec-roadmap agent with these instructions:

{tools.invoke_roadmap_agent}

Expected: Implementation roadmap with appropriately-sized phases using one of these strategies:

Strategy 1 - Feature-Based Phases (Most Common):
- Each phase delivers a complete, functional capability
- Phases align with natural feature or domain boundaries
- Clear acceptance criteria and definition of "done"
- Examples: "User Authentication", "Payment Integration", "Admin Dashboard"

Strategy 2 - Technical Layer Phases:
- Each phase completes a technical layer or infrastructure component
- Useful for foundational projects or platform work
- Examples: "Database Schema", "API Layer", "Frontend Components"

Strategy 3 - Incremental Complexity Phases:
- Start with MVP/simplest version, add complexity in subsequent phases
- Useful for exploratory or evolving requirements
- Examples: "Basic CRUD", "Add Validation & Error Handling", "Add Advanced Features"

Strategy 4 - Risk-Based Phases:
- Tackle highest-risk or most uncertain work first
- Later phases build on validated assumptions
- Useful for innovative or technically challenging projects

Choose strategy based on project characteristics. Phases should be:
- Complete enough to test and validate independently
- Small enough to maintain focus and clarity
- Large enough to deliver meaningful functionality
- Naturally ordered by dependencies

#### Step 3.2: Invoke Roadmap-Critic Agent

Use the Task tool to launch the respec-roadmap-critic agent with these instructions:

{tools.invoke_roadmap_critic}

#### Step 3.3: Get Loop Decision
```text
LOOP_DECISION_RESPONSE = {tools.decide_loop_action})
LOOP_DECISION = LOOP_DECISION_RESPONSE.status
LOOP_SCORE = LOOP_DECISION_RESPONSE.current_score
LOOP_ITERATION = LOOP_DECISION_RESPONSE.iteration

Decision options: "complete", "refine", "user_input"
```

### 4. MCP Decision Handling

**Follow LOOP_DECISION exactly. Do not override based on score assessment.**

```text
IF LOOP_DECISION == "refine":
  Display: "⟳ Iteration {{LOOP_ITERATION}} · Score: {{LOOP_SCORE}}/100 — refining roadmap"
  Return to Step 3.1 (roadmap-analyst will retrieve feedback from MCP itself)

ELIF LOOP_DECISION == "user_input":
  Display: "⚠ Quality improvements needed - user input required"

  (ONLY NOW retrieve feedback for user display)
  LATEST_FEEDBACK = {tools.get_feedback})

  Display LATEST_FEEDBACK to user with:
  - Current score and iteration
  - Key issues identified by roadmap-critic
  - Recommendations for improvement

  Use AskUserQuestion tool to present options:
  Question: "The roadmap quality is at [SCORE]/100. How would you like to proceed?"
  Options:
    1. "Proceed with current roadmap - quality is sufficient"
    2. "One more refinement iteration - address remaining issues"
    3. "Provide specific guidance for refinement"

  IF user selects option 1:
    Override MCP decision and proceed to Step 5 (Phase Extraction Planning)
  ELIF user selects option 2:
    Return to Step 3.1 for one more refinement iteration
  ELIF user selects option 3:
    Prompt for specific guidance
    Store as user feedback using store_user_feedback
    Return to Step 3.1 with user guidance

ELIF LOOP_DECISION == "complete":
  Display: "✅ Score: {{LOOP_SCORE}}/100 — roadmap approved"
  Proceed to Step 5.
  Note: Roadmap contains sparse Phase objects (iteration=0) with 4 Overview fields only.
```

### 5. Phase Extraction Planning
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

### 6. Parallel Phase Extraction
Extract sparse Phases from roadmap and save to MCP storage:

**CRITICAL UNDERSTANDING**: The roadmap agent ALREADY CREATED sparse Phase objects (iteration=0) embedded in the roadmap markdown. The create-phase agents DO NOT generate new phases - they extract existing phases from the roadmap and save them to MCP.

#### Launch Parallel Phase Extraction Agents

Launch all create-phase agents IN PARALLEL using the Task tool:

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

IMPORTANT: Launch ALL agents in a SINGLE message (multiple Task tool calls in parallel).
Do NOT launch agents sequentially. True parallelism requires one message with all invocations.

Wait for all agents to complete before proceeding to result aggregation.
```

#### Aggregate Results
```text
After all agents complete, collect results:
- SUCCESSFUL_PHASES: List of phases created successfully
- FAILED_PHASES: List of phases that failed with error details
- TOTAL_PHASES: Should equal PHASE_COUNT

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
  ✅ All phases ready for /respec-phase execution
  Next: Execute /respec-phase on individual phases
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
Suggest: "/respec-plan [PLAN_NAME] to create strategic plan"
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

Ready for Phase development through /respec-phase command execution on individual phases with validated input.
"""
