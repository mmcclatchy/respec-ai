from services.platform.models import PlanRoadmapCommandTools


def generate_roadmap_command_template(tools: PlanRoadmapCommandTools) -> str:
    return f"""---
allowed-tools:
{tools.tools_yaml}
argument-hint: [optional: phasing-preferences]
description: Transform strategic plans into multiple InitialSpecs through quality-driven refinement
---

# /specter-roadmap Command: Implementation Roadmap Orchestration

## Overview
Orchestrate the transformation of strategic plans into discrete, implementable phase roadmaps. Bridge strategic planning to technical specification through quality-driven decomposition and refinement.

## Workflow Steps

### 0. Initialize Project Context

Read project configuration:
```text
Read .specter/config.json
PROJECT_NAME = config["project_name"]
```

**Important**: PROJECT_NAME from config is used for all MCP storage operations.

### 1. Strategic Plan Retrieval and Validation
Retrieve and validate completed strategic plan from /specter-plan command:

#### Retrieve Project Plan
```text
STRATEGIC_PLAN = mcp__specter__get_project_plan_markdown(PROJECT_NAME)
IF STRATEGIC_PLAN not found:
  ERROR: "No strategic plan found for project: [PROJECT_NAME]"
  SUGGEST: "Run '/specter-plan' to create strategic plan first"
  EXIT: Graceful failure with guidance
STRUCTURED_OBJECTIVES = [Extract from strategic plan Business Objectives analysis]
PHASING_PREFERENCES = [user provided preferences or empty]
```

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

Store result as: CURRENT_ROADMAP
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

#### Step 3b: Store Roadmap in MCP
```text
TRY:
  mcp__specter__create_roadmap(project_name=PROJECT_NAME, roadmap_data=CURRENT_ROADMAP)
CATCH (if MCP storage fails):
  **CRITICAL ERROR HANDLING**:
  - DO NOT create roadmap.md files as workaround
  - DO NOT use file-based storage as alternative to MCP
  - Report the specific MCP error message to user
  - Stop workflow immediately
  - Instruct user to debug MCP server connection

  Example error message:
  "ERROR: MCP roadmap storage failed: [error details]
   Verify: MCP server running and PROJECT_NAME valid
   DO NOT create file-based workarounds - MCP storage is required."

  EXIT: Workflow terminated
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
CRITIC_FEEDBACK = mcp__specter__get_feedback(loop_id=ROADMAP_LOOP_ID, count=1)
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
Handle MCP Server response actions:

#### If MCP_DECISION == "refine"
```text
CRITIC_FEEDBACK already contains improvement recommendations
Return to Step 3a with:
  - previous_feedback: CRITIC_FEEDBACK
  - All other parameters unchanged
Roadmap agent will incorporate feedback and generate improved version
```

#### If MCP_DECISION == "user_input"
```text
Display CRITIC_FEEDBACK to user
Request targeted technical input from software engineer user:
- Specific technology stack preferences or constraints
- Architecture pattern preferences (microservices, monolith, etc.)
- Performance requirements or scaling considerations
- Integration requirements with existing systems
- Development team expertise and capacity constraints
- Timeline constraints or business priority adjustments

Store user input as USER_GUIDANCE
Return to Step 3a with:
  - previous_feedback: Combined CRITIC_FEEDBACK + USER_GUIDANCE
  - phasing_preferences: Updated with user input
```

#### If MCP_DECISION == "complete"
```text
Roadmap quality meets threshold.

**CRITICAL: The roadmap loop is complete, but the WORKFLOW CONTINUES with spec creation.**

The roadmap now contains sparse TechnicalSpec objects (iteration=0) with only the 4 Overview fields.
These specs set the big picture - create-spec agents will fill in detailed fields.

**MANDATORY NEXT STEP: Proceed to Step 5 for Spec Planning and Analysis**
DO NOT skip to final report - spec creation is REQUIRED before workflow completion.
```

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
  - Plan platform tool integration requirements
```

#### Create Spec Extraction Plan
```text
SPEC_EXTRACTION_PLAN = Generate plan for extracting specs from roadmap:
  - Phase ordering based on dependencies
  - One spec per phase (PHASE_COUNT total specs to extract and save)
  - Platform tool for external deliverables: {tools.create_spec_tool_interpolated}
  - Success criteria: Each extracted spec is sparse (iteration=0) matching roadmap content

**Remember**: Specs already exist in roadmap - we're just extracting and saving them.
```

### 6. Parallel Spec Extraction and Platform Delivery
Extract sparse TechnicalSpecs from roadmap and save to platform:

**CRITICAL UNDERSTANDING**: The roadmap agent ALREADY CREATED sparse TechnicalSpec objects (iteration=0) embedded in the roadmap markdown. The create-spec agents DO NOT generate new specs - they extract existing specs from the roadmap and save them to the platform.

#### Launch Parallel Spec Extraction Agents
```text
IMPORTANT: Launch ALL agents in a SINGLE message using multiple Task tool calls for true parallelism.

For each phase in ROADMAP_PHASES, invoke specter-create-spec agent:

Task(
    subagent_type="specter-create-spec",
    description="Extract and save spec for [phase_name]",
    prompt='''
    Extract the existing sparse TechnicalSpec (iteration=0) from roadmap and save to platform.

    **CRITICAL**: DO NOT generate new specifications. The roadmap already contains sparse TechnicalSpec objects.
    Your job is to EXTRACT the existing spec and SAVE it to the platform.

    PROJECT_NAME: [PROJECT_NAME from Step 0]
    LOOP_ID: [ROADMAP_LOOP_ID from Step 2]
    Phase Name: [phase_name from ROADMAP_PHASES]

    IMPORTANT: Use correct parameters when calling MCP tools:
    - mcp__specter__get_roadmap(project_name=PROJECT_NAME)
    - mcp__specter__store_spec(project_name=PROJECT_NAME, spec_name=PHASE_NAME, spec_markdown=...)
      * Use actual phase name (e.g., "Phase 1 - Vector Storage"), not loop_id

    The create-spec agent will:
    1. Retrieve roadmap using mcp__specter__get_roadmap
    2. Extract the existing TechnicalSpec for this phase from the roadmap
    3. Write platform deliverable using {tools.create_spec_tool_interpolated} (pass extracted spec markdown)
    4. Store in MCP using mcp__specter__store_spec
    5. Return status confirmation

    This should take seconds, not minutes - you're just extracting and saving existing content.
    '''
)

Launch all Task calls in parallel (one message with multiple tool uses).
```

#### Aggregate Results
```text
After all agents complete, collect results:
- SUCCESSFUL_SPECS: List of specs created successfully
- FAILED_SPECS: List of specs that failed with error details
- TOTAL_SPECS: Should equal PHASE_COUNT

Validate that each planned phase has a corresponding spec result.
```
Report final status with roadmap + all specs created via platform tools
```

### 7. Final Integration and Comprehensive Reporting
Complete workflow and report results with detailed status:

#### Validation: Ensure Specs Were Created
```text
CRITICAL VALIDATION STEP:
- Verify SUCCESSFUL_SPECS count > 0 (at least some specs were created)
- Verify TOTAL_SPECS = PHASE_COUNT (all phases have spec attempts)
- If SUCCESSFUL_SPECS = 0: WORKFLOW INCOMPLETE - report failure and exit
- If FAILED_SPECS > 0: PARTIAL COMPLETION - report with recovery guidance
- If SUCCESSFUL_SPECS = PHASE_COUNT: FULL SUCCESS - proceed with final report
```

#### Final Report
```text
Present completed roadmap with:
- Quality score achieved during refinement process
- Number of phases created in roadmap
- Detailed spec creation results:
  * Total specs planned from roadmap phases
  * Successfully created InitialSpec objects (count and names)
  * Platform tool confirmations (Linear tickets, GitHub issues, Notion pages)
  * Failed spec creation attempts with specific error categories
  * Recovery actions taken for partial failures
- Readiness assessment for /specter-spec command execution:
  * Phases ready for immediate technical specification
  * Phases requiring manual intervention before /specter-spec execution
  * Recommended next steps based on completion status
- Overall workflow health metrics and any warnings or recommendations
```

## Error Handling

### Graceful Degradation Patterns

#### Strategic Plan Not Available
```text
Display: "No strategic plan found for project: [project-name]"
Suggest: "/specter-plan [project-name] to create strategic plan"
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
    - Platform tool failures: Retry with alternative platform
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
    - Alternative platform options for tool failures
    - Debugging information for technical issues
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Validating strategic plan completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Handling MCP Server responses** without evaluating quality scores
- **Managing spec planning** before parallel creation
- **Orchestrating platform tool integration** for final spec creation
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **roadmap**: Phase breakdown and roadmap generation (with MCP tool access)
- **roadmap-critic**: Quality assessment and feedback
- **create-spec**: Individual InitialSpec creation + platform tool integration
- **MCP Server**: Decision logic and threshold management

## Workflow Enhancements

### Strategic Plan Validation
- Verifies analyst-critic validation completion before roadmap generation
- Provides clear error messages for incomplete plans
- Ensures high-quality input for roadmap planning

### Spec Planning Integration
- Analyzes sprint-appropriate sizing before spec creation
- Plans platform tool selection and integration
- Coordinates prerequisite ordering and dependencies

### Platform Tool Integration
- Final specs created via platform-specific tools (Linear, GitHub, Notion)
- MCP tools used for internal state management
- Platform tools used for external specification delivery

Ready for technical specification development through /specter-spec command execution on individual phases with validated input and platform integration.
"""
