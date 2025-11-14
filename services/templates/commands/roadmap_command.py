from services.platform.models import PlanRoadmapCommandTools


def generate_roadmap_command_template(tools: PlanRoadmapCommandTools) -> str:
    return f"""---
allowed-tools:
{tools.tools_yaml}
argument-hint: [project-name] [optional: phasing-preferences]
description: Transform strategic plans into multiple InitialSpecs through quality-driven refinement
---

# /specter-roadmap Command: Implementation Roadmap Orchestration

## Overview
Orchestrate the transformation of strategic plans into discrete, implementable phase roadmaps. Bridge strategic planning to technical specification through quality-driven decomposition and refinement.

## Workflow Steps

### 0. Initialize Project Context

Capture the current project directory for multi-project support:

```bash
pwd
```

Store the result as PROJECT_PATH:
```text
PROJECT_PATH = [result of pwd command]
```

**Important**: All `mcp__specter__*` tool calls must include `project_path=PROJECT_PATH` as the first parameter.

### 1. Strategic Plan Retrieval and Validation
Retrieve and validate completed strategic plan from /specter-plan command:

#### Retrieve Project Plan
```text
STRATEGIC_PLAN = mcp__specter__get_project_plan_markdown(project_name)
IF STRATEGIC_PLAN not found:
  ERROR: "No strategic plan found for project: [project_name]"
  SUGGEST: "Run '/specter-plan [project_name]' to create strategic plan first"
  EXIT: Graceful failure with guidance
STRUCTURED_OBJECTIVES = [Extract from strategic plan Business Objectives analysis]
PHASING_PREFERENCES = [user provided preferences or empty]
```

### 2. Initialize Roadmap Generation Loop
Set up MCP-managed quality refinement loop:
```text
ROADMAP_LOOP_ID = initialize_refinement_loop(loop_type='roadmap')
```

### 3. Roadmap Generation Loop
Coordinate roadmap → roadmap-critic → MCP decision cycle:

#### Phase Breakdown Generation
```text
Invoke roadmap agent with:
- Strategic Plan: ${{STRATEGIC_PLAN}}
- Phasing Preferences: ${{PHASING_PREFERENCES}}

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

#### Store Roadmap
```text
create_roadmap(project_id, roadmap_markdown)
```

#### Quality Assessment
```text
Invoke roadmap-critic agent with:
- Implementation Roadmap: ${{CURRENT_ROADMAP}}

Expected: CriticFeedback with numerical score and improvements
```

#### MCP Decision
```text
MCP_DECISION = decide_loop_next_action(
    loop_id=ROADMAP_LOOP_ID,
    current_score=QUALITY_SCORE
)
```

### 4. MCP Decision Handling
Handle MCP Server response actions:

#### If MCP_DECISION == "refine"
```text
Pass critic feedback to roadmap agent for improvements
Continue refinement cycle with updated roadmap
```

#### If MCP_DECISION == "complete"
```text
Proceed to parallel spec creation workflow
```

#### If MCP_DECISION == "user_input"
```text
Request targeted technical input from software engineer user:
- Specific technology stack preferences or constraints
- Architecture pattern preferences (microservices, monolith, etc.)
- Performance requirements or scaling considerations
- Integration requirements with existing systems
- Development team expertise and capacity constraints
- Timeline constraints or business priority adjustments
Incorporate technical feedback and continue refinement with updated context
```

### 5. Spec Planning and Analysis
Plan sprint-sized specifications before creation:

#### Retrieve Final Roadmap
```text
FINAL_ROADMAP = get_roadmap(project_id)
ROADMAP_PHASES = parse_roadmap_phases(FINAL_ROADMAP)
```

#### Analyze Phase Sizing
```text
For each phase in ROADMAP_PHASES:
  - Validate sprint-appropriate scope (1-3 weeks of work)
  - Identify prerequisite dependencies and proper ordering
  - Determine specific spec responsibilities and technical focus
  - Plan platform tool integration requirements
```

#### Create Spec Plan
```text
SPEC_CREATION_PLAN = Generate specification creation plan with:
  - Phase ordering based on dependencies
  - Sprint-sized scope validation per phase
  - Platform tool selection per spec using decision matrix:
    * Linear: For development-focused phases with clear sprint deliverables
    * GitHub: For open-source projects or technical documentation phases
    * Notion: For collaborative phases requiring stakeholder input
    * Default: Linear for most implementation phases
  - Platform tool fallback strategy:
    * Primary: User-specified or project-default platform
    * Secondary: Linear (universal development platform)
    * Tertiary: Manual spec creation with template
  - Success criteria for each specification including platform integration
```

### 6. Parallel Spec Creation
Execute planned specifications using platform tools:

#### Launch Parallel Spec Creation
```text
For each planned_spec in SPEC_CREATION_PLAN:
    Task(
        agent="specter-create-spec",
        prompt=f'''
        Project ID: {{project_id}}
        Spec Name: {{planned_spec.name}}
        Phase Context: {{planned_spec.context}}
        Platform Tools: Use {tools.create_spec_tool} for spec creation
        Sprint Scope: {{planned_spec.scope_validation}}
        '''
    )
```

#### Aggregate Results
```text
Collect all create-spec results with detailed status tracking:
- Track successful spec creations with platform tool confirmations
- Track partial failures with specific error details
- Track complete failures with diagnostic information
- Validate that each planned spec has a corresponding result
- Generate comprehensive completion report with success/failure breakdown
Report final status with roadmap + all specs created via platform tools
```

### 7. Final Integration and Comprehensive Reporting
Complete workflow and report results with detailed status:
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
