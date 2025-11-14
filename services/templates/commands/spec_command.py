from services.platform.models import SpecCommandTools


def generate_spec_command_template(tools: SpecCommandTools) -> str:
    return f"""---
allowed-tools:
{tools.tools_yaml}
argument-hint: [optional: technical-focus-area]
description: Transform strategic plans into detailed technical specifications
---

# /specter-spec Command: Technical Specification Creation

## Overview
Transform strategic plans into detailed technical specifications through quality-driven refinement. This command orchestrates technical architecture design, research integration, and platform-specific specification storage.

## Primary Responsibilities

### 1. Initialize Technical Design Process
- Retrieve strategic plan from previous `/specter-plan` phase
- Launch spec-architect agent for technical architecture development
- Initialize MCP refinement loop for specification phase

### 2. Coordinate Architecture Development  
- Guide spec-architect through technical design decisions
- Integrate existing documentation from archive scanning
- Identify external research requirements for knowledge gaps

### 3. Manage Quality Assessment Loop
- Pass specifications to spec-critic for FSDD framework evaluation
- Handle MCP Server refinement decisions based on quality scores
- Iterate until 85% quality threshold achieved (configurable)

### 4. Specification Storage
- Store final specification using configured storage tools
- Maintain platform-agnostic content structure
- Include research requirements section for future implementation

## Orchestration Pattern

```text
Main Agent (via /specter-spec)
    │
    ├── 1. Retrieve Strategic Plan
    │   └── Access plan from previous phase or user input
    │
    ├── 2. Technical Design Loop
    │   ├── Task: spec-architect (architecture + research identification)
    │   ├── Task: spec-critic (FSDD quality assessment → score)
    │   └── MCP: decide_loop_next_action(loop_id, score)
    │
    ├── 3. Handle Loop Decision
    │   ├── IF "refine" → Pass feedback to spec-architect
    │   ├── IF "complete" → Proceed to storage
    │   └── IF "user_input" → Request technical clarification
    │
    └── 4. Store Specification
        └── Platform tool to store technical specification
```

## Implementation Instructions

### Step 0: Initialize Project Context

Capture the current project directory for multi-project support:

```bash
pwd
```

Store the result as PROJECT_PATH:
```text
PROJECT_PATH = [result of pwd command]
```

**Important**: All `mcp__specter__*` tool calls must include `project_path: $PROJECT_PATH` as the first parameter.

### Step 1: Initialize Technical Design Process
Retrieve the strategic plan and set up the technical specification workflow:

```text
# Initialize MCP refinement loop
mcp__specter__initialize_refinement_loop:
  project_path: $PROJECT_PATH
  loop_type: "spec"

# Retrieve strategic plan context
STRATEGIC_PLAN_CONTEXT = [Previous /specter-plan output or user-provided plan]
TECHNICAL_FOCUS_AREA = [User argument if provided, otherwise "comprehensive architecture"]

Invoke the plan-analyst agent with this input:

Strategic Plan Source: ${{STRATEGIC_PLAN_CONTEXT}}
Context: Preparing for technical specification phase

Expected Output Format:
- Business objectives summary
- Technical requirements list
- Success criteria and constraints
- Integration points identified
```

### Step 2: Launch Architecture Development
Begin technical design with archive integration:

```text
# Execute archive scanning first
ARCHIVE_SCAN_RESULTS = Bash: ~/.claude/scripts/research-advisor-archive-scan.sh --query "technical architecture design patterns database integration API security" --output structured

# Populate context variables from Step 1 output
STRATEGIC_PLAN_SUMMARY = [plan-analyst output: business objectives, technical requirements, constraints]

Invoke the spec-architect agent with this input:

Strategic Plan Summary:
${{STRATEGIC_PLAN_SUMMARY}}

Technical Focus Area: ${{TECHNICAL_FOCUS_AREA}}

Archive Scan Results:
${{ARCHIVE_SCAN_RESULTS}}

Expected Output Format:
- Technical specification in markdown format
- Research Requirements section with existing docs and external needs
- Architecture diagrams in ASCII format
- Technology stack with justifications
```

### Step 3: Quality Assessment Loop
Pass specification to critic agent for evaluation:

```text
# Capture current specification from spec-architect output
CURRENT_SPECIFICATION = [spec-architect output: complete technical specification]

Invoke the spec-critic agent with this input:
${{CURRENT_SPECIFICATION}}

Expected Output Format:
- Overall Quality Score: [0-100 numerical value]
- Priority Improvements: [List of specific actionable suggestions]
- Strengths: [List of well-executed areas to preserve]
```

### Step 4: Handle Refinement Decisions
Process quality scores and determine next actions:

```text
# Extract quality score from spec-critic output
QUALITY_SCORE = [spec-critic output: Overall Quality Score (0-100)]
IMPROVEMENT_FEEDBACK = [spec-critic output: Priority Improvements and specific suggestions]

# MCP decision based on score
LOOP_DECISION = mcp__specter__decide_loop_next_action:
  loop_id: [from Step 1 initialization]
  current_score: ${{QUALITY_SCORE}}
  feedback: ${{IMPROVEMENT_FEEDBACK}}

# Handle MCP decision outcome
IF LOOP_DECISION == "complete":
  → Proceed to Step 5: Specification Storage
  
IF LOOP_DECISION == "refine":
  → Return to Step 2 with refined context:
  
  PREVIOUS_FEEDBACK = ${{IMPROVEMENT_FEEDBACK}}
  CURRENT_ITERATION = [increment counter]
  
  Invoke spec-architect agent with this input:
  
  Previous Specification: ${{CURRENT_SPECIFICATION}}
  Quality Assessment Feedback: ${{PREVIOUS_FEEDBACK}}
  Iteration: ${{CURRENT_ITERATION}} of 5
  
  Expected Output Format: Refined technical specification addressing feedback

IF LOOP_DECISION == "user_input":
  → Escalate with stagnation context:
  
  Present to user:
  "Technical specification has reached quality plateau at ${{QUALITY_SCORE}}%. 
  Key gaps identified: [Priority Improvements list]
  
  Please provide guidance on:
  1. [Specific technical clarification needed]
  2. [Alternative approach suggestions]  
  3. [Accept current quality level: yes/no]"

IF LOOP_DECISION == "max_iterations":
  → Present final specification with warnings:
  
  "Specification completed after maximum iterations.
  Final Quality Score: ${{QUALITY_SCORE}}%
  Remaining gaps: [Priority Improvements list]
  Recommendation: Review gaps before proceeding to implementation."
```

### Step 5: Specification Storage
Store the technical specification:

```text
Use {tools.create_spec_tool} to store the technical specification:

Title: Technical Specification: [Project Name]
Content: [Complete technical specification with research requirements]
Labels: technical-specification, architecture, phase-2
```

## Quality Gates

### Success Criteria
- **Quality Threshold**: 85% (configurable via FSDD_LOOP_SPEC_THRESHOLD)
- **Maximum Iterations**: 5 (configurable via FSDD_LOOP_SPEC_MAX_ITERATIONS)  
- **Improvement Threshold**: 5 points minimum between iterations

### Quality Assessment
Quality evaluation performed by spec-critic agent using established framework with 85% threshold for completion.

## Research Integration

### Archive Scanning Process
Archive scanning performed via `research-advisor-archive-scan.sh` to identify existing documentation and knowledge gaps for research requirements section.

### Research Requirements Format
```markdown
## Research Requirements

### Existing Documentation  
- Read: ~/.claude/best-practices/react-hooks-patterns.md
- Read: ~/.claude/best-practices/postgresql-optimization.md

### External Research Needed
- Synthesize: Best practices for integrating React with GraphQL in 2025
- Synthesize: PostgreSQL connection pooling strategies for microservices
```

## Error Handling

### Standardized Error Response Format
All error scenarios return structured responses:

```json
{{
  "error_type": "missing_plan|archive_failure|mcp_error|storage_failure|quality_plateau",
  "error_message": "Detailed error description",
  "recovery_action": "Specific recovery steps taken",
  "user_guidance": "Clear instructions for user",
  "partial_output": "Any salvageable work completed"
}}
```

### Error Scenario Implementations

#### 1. Missing Strategic Plan
```text
IF no strategic plan available:
  ERROR_RESPONSE = {{
    "error_type": "missing_plan",
    "error_message": "No strategic plan found for technical specification",
    "recovery_action": "Prompting user for plan location or /specter-plan execution",
    "user_guidance": "Please provide the strategic plan document path or run /specter-plan command first",
    "partial_output": "Technical specification template prepared"
  }}
  → Request plan location OR suggest: "Run /specter-plan [project-name] to create strategic plan first"
```

#### 2. Archive Scanning Failure
```text
IF ~/.claude/scripts/research-advisor-archive-scan.sh fails:
  ERROR_RESPONSE = {{
    "error_type": "archive_failure", 
    "error_message": "Cannot access best-practices archive for pattern identification",
    "recovery_action": "Continuing with external research only, noting archive unavailable",
    "user_guidance": "Archive unavailable - all research will be external. Specification will include comprehensive research requirements.",
    "partial_output": "Strategic plan analysis completed"
  }}
  → Continue with spec-architect but include note: "Archive unavailable - comprehensive external research required"
```

#### 3. MCP Loop State Errors
```text
IF mcp__specter__* tools unavailable:
  ERROR_RESPONSE = {{
    "error_type": "mcp_error",
    "error_message": "MCP loop state management unavailable", 
    "recovery_action": "Falling back to direct agent coordination with single iteration",
    "user_guidance": "Quality loop disabled - single-pass specification generation",
    "partial_output": "Strategic plan processed"
  }}
  → Continue with single spec-architect → spec-critic → storage workflow
```

#### 4. Storage Platform Failure
```text
IF platform storage tool fails:
  ERROR_RESPONSE = {{
    "error_type": "storage_failure",
    "error_message": "Failed to store specification in configured platform",
    "recovery_action": "Saving to local Markdown backup at docs/specter-specs/[timestamp]-spec.md",
    "user_guidance": "Platform storage failed. Specification saved locally. Check platform connectivity and configuration.",
    "partial_output": "Complete technical specification document"
  }}
  → Use Write tool to save to local file system as fallback
```

#### 5. Quality Plateau/Stagnation
```text
IF LOOP_DECISION == "user_input" (stagnation detected):
  ERROR_RESPONSE = {{
    "error_type": "quality_plateau",
    "error_message": "Specification quality plateaued at [QUALITY_SCORE]% after [CURRENT_ITERATION] iterations",
    "recovery_action": "Escalating to user for guidance on technical clarifications", 
    "user_guidance": "Quality plateau reached. Please provide: 1) Technical clarifications, 2) Alternative approaches, 3) Accept current quality level",
    "partial_output": "Technical specification at [QUALITY_SCORE]% completeness"
  }}
```

### Proactive Error Prevention
- Validate strategic plan format before processing
- Check archive accessibility before scanning  
- Test MCP tool availability before loop initialization
- Verify storage platform connectivity before final storage
- Monitor quality score trends for early stagnation detection

## Expected Output Structure

    ```markdown
    # Technical Specification: [Project Name]

    ## Overview
    [Technical summary and objectives]

    ## Architecture Design
    ### System Components
    [Component descriptions and interactions]

    ### Technology Stack
    - Frontend: [Technologies with justification]
    - Backend: [Technologies with justification]  
    - Database: [Technologies with justification]
    - Infrastructure: [Technologies with justification]

    ## Data Models
    [Entity relationships and schemas]

    ## API Design  
    [Endpoints and contracts]

    ## Security Architecture
    [Security measures and protocols]

    ## Performance Requirements
    [Metrics and benchmarks]

    ## Research Requirements
    ### Existing Documentation
    - Read: [paths to existing docs]

    ### External Research Needed  
    - Synthesize: [research prompts for current practices]

    ## Implementation Considerations
    [Technical constraints and decisions]
    ```

## Context Preservation

Maintain conversation flow while processing complex backend refinement:
- Complete conversation history passed to each agent invocation
- Technical assessments hidden from user interaction  
- Natural dialogue flow preserved despite multi-agent coordination
- Context summarization to manage size constraints

## Implementation Integration Notes

### Specification Tools
- **Storage Tool**: Platform-specific creation tool
- **Retrieval Tool**: Platform-specific retrieval tool
- **Update Tool**: Platform-specific update tool
- **Content Structure**: Platform-agnostic markdown maintained consistently
- **Research Section**: Included in specification body for all platforms

## Success Metrics

### Quantitative Targets
- **Quality Score**: ≥85% 
- **Iterations to Complete**: ≤3
- **Archive Hit Rate**: >60% of research needs covered by existing docs
- **Storage Success**: >99%

### Qualitative Indicators  
- **Technical Completeness**: All architectural decisions documented
- **Research Coverage**: All knowledge gaps identified with clear paths
- **Implementation Ready**: Sufficient detail for development teams
- **Integration**: Seamless storage and retrieval

The specification is ready for implementation planning. Recommend `/specter-build` command for next phase.
"""
