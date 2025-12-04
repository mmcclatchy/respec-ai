# /specter-build Command Specification

## Overview
The `/specter-build` command orchestrates the complete implementation workflow, transforming technical specifications into production-ready code through parallel research synthesis, implementation planning, and code development with comprehensive quality validation.

## Command Metadata

**Name**: `/specter-build`  
**Type**: User-invoked workflow command  
**Phase**: Implementation (Phases 3-4 of 4)  
**Model**: Claude Sonnet (default)  

## Invocation

### Who Invokes It
- **Primary**: End user via Claude Code CLI
- **Context**: After successful completion of `/specter-spec` command
- **Prerequisites**: Completed technical specification with research requirements

### Trigger Format
```text
/specter-build [specification-identifier]
```

## Workflow Position

```text
Technical Spec → /specter-build → Parallel Research → Planning Loop → Coding Loop → Implementation
                    │              │               │               │
                    │              ↓               ↓               ↓
                    │         Documentation    Build Plan     Production Code
                    │         Synthesis       with Tests      with Validation
                    │
                    └── Environment Discovery → Technology Detection
```

### Position in End-to-End Flow
1. **Third & Fourth Phases**: Implementation planning and code development
2. **Precedes**: Deployment and production release
3. **Dependencies**: Requires completed technical specification
4. **Output**: Production-ready implementation with tests

## Primary Responsibilities

### Core Tasks

1. **Technology Environment Discovery**
   - Execute `detect-packages.sh` to identify project stack
   - Analyze `package.json`, `requirements.txt`, `go.mod`, etc.
   - Determine testing frameworks and build tools
   - Configure implementation context

2. **Parallel Research Orchestration**
   - Parse Research Requirements from specification
   - Identify existing documentation paths (Read operations)
     - Read: [path]
     - Just collect the path, do not read the content
   - Identify external research needs (Synthesize operations)
     - Synthesize: [prompt]
   - Execute parallel operations for all research items
     - Provide the prompt to research-synthesizer
     - Collect the path provided by the research-synthesizer
   - Collect documentation paths (not content)

3. **Implementation Planning Loop**
   - Initialize MCP refinement loop for build_plan
   - Invoke `build-planner` with research paths
   - Assess plan quality with `build-critic`
   - Iterate until plan quality threshold met

4. **Code Implementation Loop**
   - Initialize MCP refinement loop for build_code
   - Invoke `build-coder` for TDD implementation
   - Validate with `build-reviewer` for quality
   - Iterate until code quality threshold met

5. **Integration & Documentation**
   - Update specification with implementation status
   - Link code changes to specification
   - Document completion in platform
   - Generate implementation summary

## Orchestration Pattern

### Complete Workflow Orchestration
```text
Main Agent (via /specter-build)
    │
    ├── 1. Retrieve Specification
    │   └── mcp_tool: get_technical_spec_markdown(spec_loop_id)
    │
    ├── 2. Environment Discovery
    │   └── Bash: detect-packages.sh → technology context
    │
    ├── 3. Parallel Research Execution
    │   ├── Parse Research Requirements section from TechnicalSpec
    │   ├── For each "Synthesize: [prompt]" item:
    │   │   └── Task: research-synthesizer (parallel) → documentation paths
    │   └── Collect: All documentation paths (Read paths + Synthesize paths)
    │
    ├── 4. Implementation Planning Loop
    │   ├── mcp_tool: initialize_refinement_loop(loop_type='build_plan')
    │   ├── Task: build-planner (with doc paths) → build plan markdown
    │   ├── mcp_tool: store_build_plan(build_plan_loop_id, build_plan_markdown)
    │   ├── Task: build-critic (assess BuildPlan) → CriticFeedback
    │   ├── mcp_tool: store_critic_feedback(critic_feedback_markdown)
    │   └── mcp_tool: decide_loop_next_action(build_plan_loop_id, quality_score)
    │
    ├── 5. Code Implementation Loop
    │   ├── mcp_tool: initialize_refinement_loop(loop_type='build_code')
    │   ├── mcp_tool: get_build_plan_markdown(build_plan_loop_id)
    │   ├── Task: build-coder (TDD approach) → implementation
    │   ├── Task: build-reviewer (assess code) → CriticFeedback
    │   ├── mcp_tool: store_critic_feedback(reviewer_feedback_markdown)
    │   └── mcp_tool: decide_loop_next_action(build_code_loop_id, quality_score)
    │
    └── 6. Completion & Documentation
        ├── Update TechnicalSpec with implementation results
        └── Production-ready code with comprehensive validation
```

### Parallel Research Pattern
```text
# Main Agent coordinates research path collection
For each item in research_requirements:

IF item starts with "Read:":
  → Extract path and add to documentation_paths list
  
IF item starts with "Synthesize:":
  → Invoke research-synthesizer agent with extracted prompt
  → Add research-synthesizer output path to documentation_paths list

Collect all documentation paths (both existing docs and research-synthesizer outputs)

Pass documentation_paths list to build-planner agent
```

## Quality Gates

### Build Planning Quality
- **Quality Threshold**: 80% (configurable via `FSDD_LOOP_BUILD_PLAN_THRESHOLD`)
- **Maximum Iterations**: 5 (configurable via `FSDD_LOOP_BUILD_PLAN_MAX_ITERATIONS`)
- **Assessment Focus**: Completeness, feasibility, test coverage

### Code Implementation Quality
- **Quality Threshold**: 95% (configurable via `FSDD_LOOP_BUILD_CODE_THRESHOLD`)
- **Maximum Iterations**: 5 (configurable via `FSDD_LOOP_BUILD_CODE_MAX_ITERATIONS`)
- **Assessment Focus**: Code quality, test passing, best practices

### Stagnation Detection
- **Both Loops**: Less than 5 points improvement over 2 iterations
- **Action**: MCP Server returns "user_input" status
- **Recovery**: Request specific guidance on blocked areas

## Research Integration Details

### Research Requirements Processing
```markdown
## Example Research Requirements Section

### Existing Documentation
- Read: ~/.claude/best-practices/react-hooks-patterns.md
- Read: ~/.claude/best-practices/testing-strategies.md

### External Research Needed
- Synthesize: Best practices for React Server Components in 2025
- Synthesize: Integration patterns for GraphQL with TypeScript
```

### Parallel Execution Strategy
```text
Main Agent identifies 4 research items:
    │
    ├── Path: react-hooks-patterns.md ─────────┐
    ├── Path: testing-strategies.md ───────────┤ PATH
    ├── Invoke: research-synthesizer (React)───┤ COLLECTION
    └── Invoke: research-synthesizer (GraphQL)─┘
                    │
                    ↓
    Collect 4 documentation paths
    (2 existing paths + 2 research-synthesizer output paths)
                    │
                    ↓
    Pass all paths to build-planner agent
    (build-planner will read all documentation)
```

### Research Synthesizer Output
```markdown
# Research: [Topic]
## Synthesized: [Timestamp]

### Key Findings
[Detailed research results]

### Best Practices
[Actionable recommendations]

### Implementation Guidance
[Specific technical guidance]
```

## Structured Data Models

### BuildPlan Model
The `/specter-build` command creates and stores structured BuildPlan models:
```python
class BuildPlan(MCPModel):
    project_name: str
    project_goal: str
    total_duration: str
    team_size: str
    primary_language: str
    framework: str
    database: str
    development_environment: str
    database_schema: str
    api_architecture: str
    frontend_architecture: str
    core_features: str
    integration_points: str
    testing_strategy: str
    code_standards: str
    performance_requirements: str
    security_implementation: str
    build_status: BuildStatus = BuildStatus.PLANNING
    creation_date: str
    last_updated: str
    build_owner: str
```

### CriticFeedback Model
Quality assessments for both planning and code phases:
```python
class CriticFeedback(MCPModel):
    loop_id: str
    critic_agent: CriticAgent  # BUILD_CRITIC, BUILD_REVIEWER
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
- **TechnicalSpec**: Specification model from `/specter-spec` phase via `get_technical_spec_markdown()`
- **Research Requirements**: Structured section in TechnicalSpec for documentation gathering
- **Environment Context**: Technology stack detection via detect-packages.sh

### Output Specifications

#### Build Plan Output
- **Structured Storage**: BuildPlan model with 21+ validated fields
- **Markdown Format**:
```markdown
# Build Plan: [Project Name]

## Project Overview
### Goal / Duration / Team Size

## Technology Stack
### Primary Language / Framework / Database / Development Environment

## Architecture
### Database Schema / API Architecture / Frontend Architecture

## Implementation Details
### Core Features / Integration Points / Testing Strategy
### Code Standards / Performance Requirements / Security Implementation

## Metadata
### Status / Creation Date / Last Updated / Build Owner
```

#### Implementation Output
- **Source Code**: Production-ready features with comprehensive tests
- **Test Results**: All test suites passing with coverage reports
- **Documentation**: Code comments, API documentation, and implementation guides
- **TechnicalSpec Updates**: Implementation status and results documented

## Error Handling

### Common Failure Scenarios

1. **Specification Not Found**
   - **Error**: "Cannot retrieve specification"
   - **Recovery**: Request specification location
   - **User Message**: "Please provide specification ID or path"

2. **Research Execution Failure**
   - **Error**: "Research synthesis failed for [topic]"
   - **Recovery**: Retry failed items, continue with available
   - **User Message**: "Some research failed. Proceeding with [X/Y] successful items."

3. **Environment Detection Failure**
   - **Error**: "Cannot detect project technology"
   - **Recovery**: Request manual technology specification
   - **User Message**: "Please specify: language, framework, test runner"

4. **Test Failures in Implementation**
   - **Error**: "Tests failing after max iterations"
   - **Recovery**: Present code with test report
   - **User Message**: "Implementation complete with test failures: [details]"

5. **Quality Threshold Not Met**
   - **Error**: "Quality below threshold after max iterations"
   - **Recovery**: Present best available with warnings
   - **User Message**: "Quality: [score]%. Key issues: [list]. Manual review recommended."

## Example Usage

### Complete Workflow Example
```text
User: /specter-build SPEC-1234

Main Agent: I'll coordinate the implementation of specification SPEC-1234. Let me start by retrieving it and setting up the workflow.

[Retrieves specification using configured platform tools]

Detecting project technology stack...
Found: React 18, TypeScript, Jest, GraphQL

Executing parallel research (4 items):
- Reading 2 existing documents...
- Synthesizing 2 external research topics...

[Parallel execution of research]

Research complete! Starting implementation planning...

[Invokes build-planner with documentation paths]

build-planner: Based on the research and specification, here's my implementation plan:

Phase 1: Setup GraphQL Schema
- Define type definitions
- Create resolver structure
- Setup Apollo Server

Phase 2: React Components
- Implement feedback list component
- Create detail view with AI insights
- Add filtering and sorting

Phase 3: Integration & Testing
- Connect frontend to GraphQL
- Write comprehensive tests
- Performance optimization

[Score: 82% - approved by build-critic]

Main Agent: Plan approved! Coordinating code implementation...

[Invokes build-coder]

build-coder: Implementing with TDD approach:

1. Writing tests for GraphQL schema...
2. Implementing schema to pass tests...
3. Writing component tests...
4. Implementing components...

[Shows code implementation]

[Score: 96% - approved by build-reviewer]

Main Agent: Implementation complete!
- All tests passing ✓
- Code quality: 96%
- Updated specification with implementation details
- Ready for deployment

Summary:
- 15 files modified
- 42 tests passing
- 0 security issues
- Performance benchmarks met
```

## Implementation Notes

### Key Considerations for Claude Code

1. **Parallel Execution Management**
   - Use Promise.all or equivalent for research tasks
   - Handle partial failures gracefully
   - Timeout long-running research (30s max)

2. **Documentation Path Handling**
   - Pass paths, not content, to build-planner
   - Let build-planner read documents as needed
   - Avoid context overflow from large documents

3. **Technology Detection**
   - Cache detection results for session
   - Support multiple language projects
   - Fallback to user input if ambiguous

4. **Loop State Separation**
   - Maintain separate loop IDs for plan and code
   - Clear messaging about which loop is active
   - Show progress for each phase

5. **TDD Enforcement**
   - Ensure build-coder writes tests first
   - Validate test execution before implementation
   - Require green tests for completion

## Dependencies and Integration Points

### Required Components
- **MCP Server**: Dual loop state management
- **build-planner agent**: Implementation planning
- **build-critic agent**: Plan quality assessment
- **build-coder agent**: TDD implementation
- **build-reviewer agent**: Code quality validation
- **research-synthesizer agent**: External research

### MCP Tools Used
**Specification Retrieval:**
- `get_technical_spec_markdown(spec_loop_id)` - Retrieve TechnicalSpec from /specter-spec phase

**Build Planning Loop (build_plan):**
- `initialize_refinement_loop(loop_type='build_plan')` - Create build planning loop
- `store_build_plan(build_plan_loop_id, build_plan_markdown)` - Store BuildPlan model
- `store_critic_feedback(feedback_markdown)` - Store build-critic CriticFeedback
- `decide_loop_next_action(build_plan_loop_id, current_score)` - Planning decision engine
- `get_build_plan_markdown(build_plan_loop_id)` - Retrieve plan for code phase

**Code Implementation Loop (build_code):**
- `initialize_refinement_loop(loop_type='build_code')` - Create code implementation loop
- `store_critic_feedback(feedback_markdown)` - Store build-reviewer CriticFeedback
- `decide_loop_next_action(build_code_loop_id, current_score)` - Implementation decision engine

**Feedback & Monitoring:**
- `get_feedback(loop_id, count)` - Retrieve recent feedback for context
- `get_loop_status(loop_id)` - Monitor loop state (optional)
- `list_build_plans(count)` - List existing build plans
- `delete_build_plan(loop_id)` - Clean up build plans

### Shell Scripts
- `~/.claude/scripts/detect-packages.sh`

### Environment Variables
- `FSDD_LOOP_BUILD_PLAN_THRESHOLD`: Plan quality (default: 80)
- `FSDD_LOOP_BUILD_PLAN_MAX_ITERATIONS`: Plan iterations (default: 5)
- `FSDD_LOOP_BUILD_CODE_THRESHOLD`: Code quality (default: 95)
- `FSDD_LOOP_BUILD_CODE_MAX_ITERATIONS`: Code iterations (default: 5)

## Success Metrics

### Quantitative Metrics
- **Plan Quality Score**: Target ≥80%
- **Code Quality Score**: Target ≥95%
- **Test Coverage**: Target >80%
- **Build Success Rate**: Target 100%
- **Research Success Rate**: Target >90%

### Qualitative Metrics
- **Implementation Completeness**: All specification requirements met
- **Code Maintainability**: Following best practices
- **Documentation Quality**: Clear and comprehensive
- **Performance**: Meeting specification benchmarks

## Related Documentation
- **Previous Phase**: [`/specter-spec` Command Specification](spec.md)
- **Planning Agent**: [`build-planner` Agent Specification](../agents/specter-build-planner.md)
- **Coding Agent**: [`build-coder` Agent Specification](../agents/specter-build-coder.md)
- **Research Agent**: [`research-synthesizer` Agent Specification](../agents/research-synthesizer.md)
- **Refinement**: [`/refine-build-plan` Command](refine-build-plan.md) and [`/refine-build-code` Command](refine-build-code.md)
