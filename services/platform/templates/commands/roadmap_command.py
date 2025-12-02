from services.platform.models import PlanRoadmapCommandTools


def generate_roadmap_command_template(tools: PlanRoadmapCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [project-name] [optional: phasing-preferences]
description: Transform strategic plans into multiple InitialSpecs through quality-driven refinement
---

# /specter-roadmap Command: Implementation Roadmap Orchestration

## Overview
Orchestrate the transformation of strategic plans into discrete, implementable phase roadmaps. Bridge strategic planning to technical specification through quality-driven decomposition and refinement.

## Workflow Steps

### 0a. Load Existing Documents from Platform

Load project plan and all existing specs from platform:

```text
# Load Project Plan
{tools.sync_project_plan_instructions}

# Load All Existing Specs
{tools.sync_all_specs_instructions}
```

### 0. Extract Command Arguments

Parse command arguments from user input:
```text
PROJECT_NAME = [first argument from command - the project name]
PHASING_PREFERENCES = [second argument if provided, otherwise empty string]
```

**Important**: PROJECT_NAME from command arguments is used for all MCP storage operations.

### 1. Strategic Plan Retrieval and Validation
Retrieve and validate completed strategic plan from /specter-plan command:

#### Retrieve Project Plan
```text
STRATEGIC_PLAN = mcp__specter__get_project_plan_markdown(PROJECT_NAME)
IF STRATEGIC_PLAN not found:
  ERROR: "No strategic plan found for project: [PROJECT_NAME]"
  SUGGEST: "Run '/specter-plan [PROJECT_NAME]' to create strategic plan first"
  EXIT: Graceful failure with guidance
STRUCTURED_OBJECTIVES = [Extract from strategic plan Business Objectives analysis]
```

Note: PHASING_PREFERENCES already extracted from command arguments in Step 0.

### 2. Initialize Roadmap Generation Loop
Set up MCP-managed quality refinement loop:
```text
ROADMAP_LOOP_ID = mcp__specter__initialize_refinement_loop(loop_type='roadmap')
```

### 3. Roadmap Generation Loop
Coordinate roadmap → roadmap-critic → MCP decision cycle:

#### Step 3a: Invoke Roadmap Agent
```text
Invoke: specter-roadmap
Input:
  - loop_id: ROADMAP_LOOP_ID
  - project_name: PROJECT_NAME
  - phasing_preferences: PHASING_PREFERENCES
  - previous_feedback: CRITIC_FEEDBACK (if this is a refinement iteration)

**CRITICAL**: Capture the agent's complete output markdown as CURRENT_ROADMAP.
The agent returns the full roadmap markdown but does NOT store it.
You MUST store this output in Step 3b using mcp__specter__create_roadmap.

CURRENT_ROADMAP = [complete markdown output from roadmap agent]
```

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
```


#### Step 3b: Store Roadmap in MCP (MANDATORY - DO NOT SKIP)

**CRITICAL: This step MUST be executed immediately after Step 3a completes.**

The roadmap agent returns markdown but does NOT store it. YOU must store it now.

```text
STORE_RESULT = mcp__specter__create_roadmap(
    project_name=PROJECT_NAME,
    roadmap_data=CURRENT_ROADMAP
)

IF STORE_RESULT contains error:
  **CRITICAL ERROR - STOP WORKFLOW**:
  - Report the specific MCP error message to user
  - DO NOT create roadmap.md files as workaround
  - DO NOT use file-based storage as alternative to MCP
  - DO NOT proceed to Step 3c

  Example error message:
  "ERROR: MCP roadmap storage failed: [error details]
   Verify: MCP server running and PROJECT_NAME valid
   DO NOT create file-based workarounds - MCP storage is required."

  EXIT: Workflow terminated

VERIFY storage succeeded:
VERIFICATION = mcp__specter__get_roadmap(project_name=PROJECT_NAME)

IF VERIFICATION fails:
  ERROR: "Roadmap storage verification failed - roadmap was not saved to MCP"
  EXIT: Workflow terminated

Display to user: "✓ Roadmap stored in MCP successfully"
```

#### Step 3c: Invoke Roadmap-Critic Agent
```text
Invoke: specter-roadmap-critic
Input:
  - project_name: PROJECT_NAME
  - loop_id: ROADMAP_LOOP_ID

Roadmap-critic will:
1. Retrieve roadmap from MCP using project_name
2. Evaluate against FSDD framework
3. Store feedback in MCP loop using loop_id
```

#### Step 3d: Get Feedback and Extract Score
```text
CRITIC_FEEDBACK = mcp__specter__get_feedback(loop_id=ROADMAP_LOOP_ID, count=2)
Note: Retrieves 2 most recent iterations for stagnation detection (<10 points improvement threshold)
Extract QUALITY_SCORE from CRITIC_FEEDBACK markdown (look for "Overall Score: [number]")
```

#### Step 3e: MCP Loop Decision
```text
MCP_DECISION = mcp__specter__decide_loop_next_action(
    loop_id=ROADMAP_LOOP_ID,
    current_score=QUALITY_SCORE
)

Display to user:
- Quality Score: QUALITY_SCORE
- MCP Decision: MCP_DECISION
```

### 4. MCP Decision Handling

**Follow MCP_DECISION exactly. Do not override based on score assessment.**

#### If MCP_DECISION == "refine"
Return to Step 3a with previous_feedback: CRITIC_FEEDBACK
Execute Steps 3b-3e again.

#### If MCP_DECISION == "user_input"
Display CRITIC_FEEDBACK to user.
Request technical input (stack preferences, architecture patterns, constraints).
Return to Step 3a with previous_feedback: CRITIC_FEEDBACK + user input.
Execute Steps 3b-3e again.

#### If MCP_DECISION == "complete"
Proceed to Step 5.
Note: Roadmap contains sparse TechnicalSpec objects (iteration=0) with 4 Overview fields only.

### 5. Spec Extraction Planning
Plan extraction of sparse TechnicalSpecs from roadmap before parallel processing:

#### Retrieve Final Roadmap
```text
FINAL_ROADMAP = mcp__specter__get_roadmap(project_name=PROJECT_NAME)
Parse FINAL_ROADMAP to extract:
  - ROADMAP_PHASES: List of all phases with names, durations, dependencies
  - PHASE_COUNT: Total number of phases
```

#### Analyze Phase Sizing
```text
For each phase in ROADMAP_PHASES:
  - Validate sprint-appropriate scope (2-4 weeks of work per roadmap design)
  - Identify prerequisite dependencies and proper ordering
  - Determine specific spec responsibilities and technical focus
```

#### Create Spec Extraction Plan
```text
SPEC_EXTRACTION_PLAN = Generate plan for extracting specs from roadmap:
  - Phase ordering based on dependencies
  - One spec per phase (PHASE_COUNT total specs to extract and save)
  - Success criteria: Each extracted spec is sparse (iteration=0) matching roadmap content

**Remember**: Specs already exist in roadmap - we're just extracting and saving them to MCP.
```

### 6. Parallel Spec Extraction
Extract sparse TechnicalSpecs from roadmap and save to MCP storage:

**CRITICAL UNDERSTANDING**: The roadmap agent ALREADY CREATED sparse TechnicalSpec objects (iteration=0) embedded in the roadmap markdown. The create-spec agents DO NOT generate new specs - they extract existing specs from the roadmap and save them to MCP.

#### Launch Parallel Spec Extraction Agents
```text
IMPORTANT: Launch ALL agents in a SINGLE message using multiple agent invocations for true parallelism.

For each phase in ROADMAP_PHASES, invoke specter-create-spec agent:

Invoke: specter-create-spec
Input:
  - project_name: PROJECT_NAME
  - spec_name: [phase_name from ROADMAP_PHASES]
  - loop_id: ROADMAP_LOOP_ID

Launch all invocations in parallel (one message with multiple agent invocations).
```

#### Aggregate Results
```text
After all agents complete, collect results:
- SUCCESSFUL_SPECS: List of specs created successfully
- FAILED_SPECS: List of specs that failed with error details
- TOTAL_SPECS: Should equal PHASE_COUNT

Validate that each planned phase has a corresponding spec result.
```

### 6.5. Verify Spec Creation (MANDATORY)

**CRITICAL**: Verify actual MCP storage, not agent completion messages.

Verification Sequence:
```text
STEP 1: Query MCP Storage
STORED_SPECS = mcp__specter__list_specs(project_name=PROJECT_NAME)

STEP 2: Compare Results
EXPECTED_COUNT = PHASE_COUNT (from Step 5)
ACTUAL_COUNT = length of STORED_SPECS

STEP 3: Detailed Verification
For each phase in ROADMAP_PHASES:
  EXPECTED_SPEC_NAME = phase.name

  IF EXPECTED_SPEC_NAME in STORED_SPECS:
    STATUS = "✅ SUCCESS"
    VERIFY_SPEC = mcp__specter__get_spec_markdown(
      project_name=PROJECT_NAME,
      spec_name=EXPECTED_SPEC_NAME
    )
    CONFIRM: Spec contains valid TechnicalSpec markdown
  ELSE:
    STATUS = "❌ FAILED"
    LOG: Spec not found in MCP storage despite agent completion

  Record: (phase_name, status, evidence)

STEP 4: Generate Evidence-Based Report
Report actual verification results:
  - Total phases: PHASE_COUNT
  - Successfully stored: [count with ✅]
  - Failed storage: [count with ❌]
  - Evidence: MCP list_specs response

DO NOT rely on agent completion messages.
Only report success for specs verified in MCP storage.
```

### 7. Final Integration and Comprehensive Reporting

Present verified results only:

```text
**Roadmap Completed**:
- Quality Score: [score from Step 3e]
- Total Phases: [PHASE_COUNT from Step 5]

**Spec Storage Verification** (from Step 6.5):
- Specs in MCP Storage: [ACTUAL_COUNT] of [EXPECTED_COUNT]
- Verified Specs: [list of ✅ spec names]
- Missing Specs: [list of ❌ spec names]
- Evidence: mcp__specter__list_specs output

**Readiness Assessment**:
IF ACTUAL_COUNT == EXPECTED_COUNT:
  ✅ All phases ready for /specter-spec execution
  Next: Execute /specter-spec on individual phases
ELSE:
  ⚠️ Partial completion - manual intervention required
  Missing: [list specific phase names without MCP storage]
  Action: Review Step 6 agent failures and retry failed specs

**Next Steps**:
[Provide specific guidance based on actual verification results]
```

## Error Handling

### Graceful Degradation Patterns

#### Strategic Plan Not Available
```text
Display: "No strategic plan found for project: [PROJECT_NAME]"
Suggest: "/specter-plan [PROJECT_NAME] to create strategic plan"
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

#### Parallel Spec Creation Failures
```text
IF some create-spec agents fail:
  Continue with successful spec creations
  Categorize failures by type:
    - Phase context extraction failures: Provide manual spec template
    - MCP storage failures: Retry storage operation once
    - Complete agent failures: Log error and continue with remaining specs
  Report detailed completion status:
    - Total specs planned: X
    - Successfully created: Y
    - Failed with recovery: Z
    - Failed completely: W
  Provide specific guidance for each failed spec:
    - Manual creation templates for context extraction failures
    - Debugging information for technical issues
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Validating strategic plan completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Handling MCP Server responses** without evaluating quality scores
- **Managing spec planning** before parallel creation
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **roadmap**: Phase breakdown and roadmap generation (with MCP tool access)
- **roadmap-critic**: Quality assessment and feedback
- **create-spec**: Individual InitialSpec extraction and MCP storage
- **MCP Server**: Decision logic and threshold management

## Workflow Enhancements

### Strategic Plan Validation
- Verifies analyst-critic validation completion before roadmap generation
- Provides clear error messages for incomplete plans
- Ensures high-quality input for roadmap planning

### Spec Planning Integration
- Analyzes sprint-appropriate sizing before spec creation
- Coordinates prerequisite ordering and dependencies
- Manages MCP storage for spec tracking

Ready for technical specification development through /specter-spec command execution on individual phases with validated input.
"""
