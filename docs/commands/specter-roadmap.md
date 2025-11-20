# /specter-roadmap Command Specification

## Overview
The `/specter-roadmap` command transforms strategic plans into phased implementation roadmaps. It orchestrates the decomposition of high-level business objectives into discrete, spec-ready implementation phases through quality-driven refinement.

## Command Metadata

**Name**: `/specter-roadmap`  
**Type**: Implementation planning orchestrator  
**Phase**: Strategic Planning → Implementation Roadmap (Bridge to Technical Specification)  
**Model**: Claude Sonnet (default)

## Invocation

### Who Invokes It
- **Primary**: End user via Claude Code CLI
- **Context**: After successful completion of `/specter-plan` command
- **Prerequisites**: Completed strategic plan document with structured objectives

### Trigger Format
```text
/specter-roadmap [optional: phasing-preferences]
```

### Parameters
- **phasing-preferences**: Optional user guidance on phase boundaries (e.g., "2-week sprints", "MVP in 3 months")

## Workflow Position

```text
Strategic Plan → /specter-roadmap → [roadmap ↔ roadmap-critic loop] → Implementation Roadmap
                                           ↓                                          ↓
                                   Phase Breakdown                          Quality Assessment
                                           ↓                                          ↓
                                   Dependency Mapping                      Refinement Decision
                                           ↓
                                    Ready for /specter-spec calls (per phase)
```

### Position in End-to-End Flow
1. **Bridge Phase**: Connects strategic planning to technical specification
2. **Precedes**: Multiple `/specter-spec` command invocations (one per phase)
3. **Dependencies**: Requires completed strategic plan and objectives analysis
4. **Output Used By**: `/specter-spec` command for phase-specific technical specifications

## Primary Responsibilities

### Core Tasks

1. **Strategic Plan Context Gathering**
   - Access completed strategic plan from `/specter-plan` command output
   - Retrieve structured objectives from plan-analyst processing
   - Capture optional user phasing preferences
   - Establish baseline for roadmap generation

2. **Implementation Decomposition Orchestration**
   - Initialize MCP refinement loop for roadmap generation
   - Launch `roadmap` agent for phase breakdown
   - Manage iterative roadmap development process
   - Coordinate phase scoping and dependency mapping

3. **Quality Assessment Loop Management**
   - Invoke `roadmap-critic` agent for roadmap evaluation
   - Process quality scores and feedback through MCP Server
   - Handle refinement decisions (refine/complete/user_input)
   - Monitor iteration count and improvement trends

4. **Refinement Cycle Coordination**
   - Route critic feedback to roadmap for improvements
   - Maintain roadmap context across iterations
   - Manage stagnation detection and user escalation
   - Ensure MCP Server completion criteria before finishing

5. **Final Roadmap Preparation**
   - Validate completed roadmap structure and content
   - Prepare phase-specific contexts for downstream `/specter-spec` calls
   - Document implementation sequence and dependencies
   - Ensure smooth handoff to technical specification phase

## Orchestration Pattern

### Complete Workflow Orchestration
```text
Main Agent (via /specter-roadmap)
    │
    ├── 1. Retrieve Strategic Plan
    │   └── mcp_tool: get_project_plan_markdown(plan_loop_id)
    │
    ├── 2. Initialize Roadmap MCP Loop
    │   └── mcp_tool: initialize_refinement_loop(loop_type='roadmap')
    │
    ├── 3. Roadmap Generation Loop
    │   ├── Task: roadmap (phase breakdown → roadmap markdown)
    │   ├── mcp_tool: create_roadmap(project_name, roadmap_markdown)
    │   ├── Task: roadmap-critic (quality assessment → CriticFeedback)
    │   ├── mcp_tool: store_critic_feedback(critic_feedback_markdown)
    │   └── mcp_tool: decide_loop_next_action(roadmap_loop_id, quality_score)
    │
    ├── 4. Handle Loop Decision
    │   ├── IF "refine" → Pass structured feedback to roadmap
    │   ├── IF "complete" → Finalize Roadmap model and proceed
    │   └── IF "user_input" → Request roadmap clarification with feedback context
    │
    └── 5. Finalize & Prepare for Spec Phase
        ├── mcp_tool: get_roadmap(project_name)
        └── Roadmap ready for multiple /specter-spec command invocations
```

### Data Flow Between Components
- **Main Agent → MCP Server**: `get_project_plan_markdown(plan_loop_id)` - Retrieve strategic plan
- **Main Agent → roadmap**: Strategic plan + objectives + preferences
- **roadmap → Main Agent**: Implementation roadmap with phased breakdown (markdown)
- **Main Agent → MCP Server**: `create_roadmap(project_name, roadmap_markdown)` - Create Roadmap model
- **Main Agent → roadmap-critic**: Roadmap for FSDD assessment
- **roadmap-critic → Main Agent**: Structured CriticFeedback (markdown format)
- **Main Agent → MCP Server**: `store_critic_feedback(feedback_markdown)` - Store feedback model
- **Main Agent → MCP Server**: `decide_loop_next_action(roadmap_loop_id, quality_score)` - Decision logic
- **MCP Server → Main Agent**: Next action (refine/complete/user_input) with loop state
- **Main Agent → MCP Server**: `get_roadmap(project_name)` - Final retrieval for /specter-spec phase

## Structured Data Models

### Roadmap Model
The `/specter-roadmap` command creates and stores structured Roadmap models:
```python
class Roadmap(MCPModel):
    project_name: str
    project_goal: str
    total_duration: str
    team_size: str
    roadmap_budget: str
    specs: list[InitialSpec] = Field(default_factory=list)
    critical_path_analysis: str
    key_risks: str
    mitigation_plans: str
    buffer_time: str
    development_resources: str
    infrastructure_requirements: str
    external_dependencies: str
    quality_assurance_plan: str
    technical_milestones: str
    business_milestones: str
    quality_gates: str
    performance_targets: str
    roadmap_status: RoadmapStatus = RoadmapStatus.DRAFT
    spec_count: int = 0
```

### CriticFeedback Model
Quality assessments stored as structured feedback:
```python
class CriticFeedback(MCPModel):
    loop_id: str
    critic_agent: CriticAgent.ROADMAP_CRITIC
    iteration: int
    overall_score: int  # 0-100
    assessment_summary: str
    detailed_feedback: str
    key_issues: list[str]
    recommendations: list[str]
    timestamp: datetime
```

## Input/Output Specifications

### Input Requirements
- **ProjectPlan**: ProjectPlan model from `/specter-plan` phase via `get_project_plan_markdown()`
- **Phasing Preferences**: Optional user guidance on phase structure and timing
- **Format**: Roadmap markdown structure

### Output Specifications
- **Primary Output**: Roadmap model stored in MCP Server + implementation roadmap markdown
- **Structured Storage**: Roadmap with 18+ validated fields for `/specter-spec` consumption
- **Markdown Format**:
```markdown
# Project Roadmap: [Project Name]

## Project Details
### Project Goal / Total Duration / Team Size / Budget

## Specifications
[Phased implementation breakdown with InitialSpec objects]

## Risk Assessment
### Critical Path Analysis / Key Risks / Mitigation Plans / Buffer Time

## Resource Planning
### Development Resources / Infrastructure Requirements
### External Dependencies / Quality Assurance Plan

## Success Metrics
### Technical Milestones / Business Milestones
### Quality Gates / Performance Targets

## Metadata
### Status / Spec Count
```

## Quality Gates

### Success Criteria
- **Quality Threshold**: 85% (configurable via `FSDD_LOOP_ROADMAP_THRESHOLD`)
- **Maximum Iterations**: 5 (configurable via `FSDD_LOOP_ROADMAP_MAX_ITERATIONS`)
- **Improvement Threshold**: 5 points minimum between iterations

### Stagnation Detection
- **Trigger**: Less than 5 points improvement over 2 consecutive iterations
- **Action**: MCP Server returns "user_input" status
- **Recovery**: Request specific guidance on roadmap areas

### FSDD Assessment Points
The roadmap-critic evaluates roadmaps against:
1. **Phase Scoping** - Each phase delivers user value within reasonable timeframe
2. **Dependency Management** - Clear sequencing and prerequisites without circular dependencies
3. **Scope Clarity** - Specific deliverables and explicit boundaries per phase
4. **Implementation Readiness** - Sufficient detail and context for `/specter-spec` command processing
5. **Resource Balance** - Realistic complexity distribution across phases
6. **Risk Distribution** - Critical items appropriately phased with mitigation strategies
7. **Timeline Feasibility** - Realistic duration estimates and milestone definitions
8. **Success Criteria** - Clear, measurable outcomes for each phase
9. **Specification Planning** - Adequate preparation for downstream `/specter-spec` calls
10. **Integration Strategy** - How phases connect and build upon each other
11. **Quality Assurance** - Testing and validation approach per phase
12. **Performance Targets** - Measurable performance criteria across phases

## Output Structure

### Implementation Roadmap Format

```markdown
# Implementation Roadmap: [Project Name]

## Overview
[Summary of phasing strategy and approach]

## Phase Summary
- **Total Phases**: [Number]
- **Estimated Duration**: [Overall timeline]
- **Critical Path**: [Key dependencies]

## Phase 1: [Foundation/Core/Name]
**Duration**: [Timeframe]
**Priority**: Critical/High/Medium
**Dependencies**: None

### Scope
[Clear description of what this phase includes]

### Deliverables
- [Specific feature or capability]
- [Specific feature or capability]
- [Specific feature or capability]

### Technical Focus
[Key technical areas for spec development]

### Success Criteria
- [Measurable outcome]
- [Measurable outcome]

### Spec Context
[Information needed for /specter-spec command]
- Focus Areas: [Technical domains]
- Key Decisions: [Architecture choices needed]
- Research Needs: [Knowledge gaps to address]

## Phase 2: [Name]
**Duration**: [Timeframe]
**Priority**: High/Medium
**Dependencies**: Phase 1 completion

### Scope
[Clear description]

### Deliverables
[Feature list]

### Technical Focus
[Key areas]

### Success Criteria
[Measurable outcomes]

### Spec Context
[/specter-spec guidance]

[Additional phases following same structure]

## Risk Mitigation
[Cross-phase risks and mitigation strategies]

## Integration Points
[How phases connect and dependencies between them]
```

## Agent Coordination

### roadmap Agent
- **Input**: Strategic plan + structured objectives
- **Output**: Multi-phase implementation roadmap
- **Focus**: Breaking down requirements into implementable chunks

### roadmap-critic Agent
- **Input**: Implementation roadmap
- **Output**: Quality score + improvement feedback
- **Focus**: Validating phase scoping and dependencies

## Error Handling

### Missing Strategic Plan
```text
IF no strategic plan available:
  Display: "No strategic plan found. Please run /specter-plan command first."
  Suggest: "/specter-plan [project-name] to create strategic plan"
  Exit gracefully
```

### Invalid Plan Format
```text
IF strategic plan format unrecognizable:
  Attempt: Parse available sections
  Continue: With partial information
  Note: Document limitations in roadmap
```

### Agent Failures
```text
IF roadmap fails:
  Retry: Once with simplified input
  Fallback: Create basic 3-phase roadmap
  Document: Limitations in output

IF roadmap-critic fails:
  Continue: Without quality loop
  Note: "Manual review recommended"
  Provide: Best-effort roadmap
```

### MCP Loop Failures
```text
IF loop initialization fails:
  Continue: Single-pass roadmap generation
  Skip: Refinement cycles
  Note: Quality assessment unavailable
```

## Example Usage

### Complete Workflow Example
```text
User: /specter-roadmap

Main Agent: I'll transform your strategic plan into a phased implementation roadmap. Let me retrieve the plan and break it down into manageable phases.

[Retrieves strategic plan using configured platform tools]

Analyzing strategic plan for AI-powered customer feedback system...

[Invokes roadmap agent]

roadmap: Creating phased roadmap based on business objectives and dependencies. Analyzing technical components for optimal sequencing...

Phase 1: Core Infrastructure (4 weeks)
- Authentication & data models
- Basic API framework
- Database setup

Phase 2: AI Integration (6 weeks)
- Machine learning pipeline
- Classification service
- Training data pipeline

Phase 3: User Interface (4 weeks)
- Dashboard development
- Feedback visualization
- User management

Phase 4: Advanced Features (4 weeks)
- Real-time analytics
- Advanced reporting
- Performance optimization

[Creates roadmap using create_roadmap tool]

[Main Agent invokes roadmap-critic]

roadmap-critic: Assessing roadmap quality...
- Phase scoping: 85%
- Dependencies: 78%
- Risk distribution: 72%
Overall Score: 78% - needs better risk mitigation planning

[Score: 78% - Main Agent receives "refine" decision from MCP Server]

roadmap: Improving risk assessment and mitigation strategies...

Adding:
- Buffer time for ML model training
- Parallel development opportunities
- Rollback strategies per phase
- Performance benchmarks

[Final score: 88% - Main Agent receives "complete" decision]

Main Agent: Implementation roadmap completed!
- Quality score: 88%
- 4 phases over 18 weeks
- 12 InitialSpec objects created
- Ready for phase-specific technical specifications

Use /specter-spec to create technical specifications for each phase.
```

### With Phasing Preferences
```text
User: /specter-roadmap "prefer 2-week sprints, MVP by month 3"

Main Agent: Creating roadmap with 2-week sprint phases targeting MVP delivery in 3 months...
```

## Dependencies and Integration Points

### Required Components
- **MCP Server**: Loop state management and decision logic
- **roadmap agent**: Phase breakdown and roadmap generation
- **roadmap-critic agent**: Quality assessment and feedback

### MCP Tools Used
**Roadmap Generation Workflow:**
- `get_project_plan_markdown(plan_loop_id)` - Retrieve strategic plan from /specter-plan phase
- `initialize_refinement_loop(loop_type='roadmap')` - Create roadmap refinement loop
- `create_roadmap(project_name, roadmap_markdown)` - Store Roadmap model
- `store_critic_feedback(feedback_markdown)` - Store structured CriticFeedback
- `decide_loop_next_action(roadmap_loop_id, current_score)` - Loop decision engine
- `get_roadmap(project_name)` - Retrieve final roadmap for /specter-spec phase
- `get_loop_status(roadmap_loop_id)` - Monitor loop state (optional)
- `get_feedback_history(roadmap_loop_id, count)` - Retrieve recent feedback for context

**Unified Spec Management Tools:**
- `store_spec(project_name, spec_name, spec_markdown)` - Store spec with auto-versioning
- `get_spec_markdown(project_name, spec_name, loop_id)` - Retrieve spec (by project OR loop)
- `list_specs(project_name)` - List all specs in project
- `delete_spec(project_name, spec_name)` - Remove spec from storage
- `link_loop_to_spec(loop_id, project_name, spec_name)` - Link refinement loop to spec
- `unlink_loop(loop_id)` - Remove loop mapping

### Environment Variables
- `FSDD_LOOP_ROADMAP_THRESHOLD`: Quality threshold (default: 85)
- `FSDD_LOOP_ROADMAP_MAX_ITERATIONS`: Maximum iterations (default: 5)

## MCP Server Response Handling

### Decision Processing
The command handles three MCP Server responses:

1. **refine**:
   - Pass critic feedback to roadmap for improvements
   - Continue refinement cycle with updated roadmap
   - Maintain context across iterations

2. **complete**:
   - Accept current roadmap as final
   - Prepare phase-specific contexts for downstream `/specter-spec` calls  
   - Present completed roadmap to user

3. **user_input**:
   - Request additional user guidance on phasing preferences
   - Incorporate user feedback into next refinement cycle
   - Continue with enhanced requirements

## Integration Notes

### With /specter-plan Command
- Consumes strategic plan output
- Uses structured objectives from plan-analyst
- Maintains context from planning phase

### With /specter-spec Command
- Provides phase-specific context for targeted specification
- Enables incremental development through phased specs
- Supports multiple `/specter-spec` cycles per roadmap

### With /specter-build Command  
- Enables phased implementation approach
- Supports iterative delivery model
- Facilitates progress tracking across phases

## Platform-Specific Behavior

### Platform-Agnostic Design
The `/specter-roadmap` command operates identically across all platforms (Linear, GitHub, Markdown) as it produces platform-independent roadmaps. Platform-specific behavior only emerges in subsequent `/specter-spec` and `/specter-build` phases.

## Success Metrics

### Quantitative Metrics
- **Quality Score**: Target ≥85%
- **Iterations to Complete**: Target ≤3
- **Phase Coverage**: Target 100% of strategic objectives
- **Spec Generation Success**: Target >95%

### Qualitative Metrics
- **Implementation Readiness**: All phases have sufficient detail for `/specter-spec`
- **Dependency Clarity**: Clear sequencing without circular dependencies
- **Risk Mitigation**: Comprehensive strategies for identified risks
- **Value Delivery**: Each phase delivers measurable user value

## Related Documentation
- **Previous Phase**: [`/specter-plan` Command Specification](plan.md)
- **Next Phase**: [`/specter-spec` Command Specification](spec.md)
- **Primary Agent**: [`roadmap` Agent Specification](../agents/specter-roadmap.md)
- **Quality Agent**: [`roadmap-critic` Agent Specification](../agents/roadmap-critic.md)
- **MCP Tools**: [MCP Tools Specification](../MCP_TOOLS_SPECIFICATION.md)
