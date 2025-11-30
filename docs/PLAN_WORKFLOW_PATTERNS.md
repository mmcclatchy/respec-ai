# Plan Workflow Patterns: /specter-plan Command Analysis

## Executive Summary

This document captures essential patterns and lessons learned from developing the `/specter-plan` command within the Spec-Driven Development workflow system. Through iterative refinement and architectural evolution, several key patterns emerged that significantly improved command reliability, maintainability, and user experience. These insights provide actionable guidance for future command development.

## Command Architecture Patterns

### 1. Commands as Orchestrators, Not Executors

**Principle**: Commands should coordinate specialized agents rather than performing work directly.

**Pattern**:
```text
Main Agent (Command)
├── Initializes workflow state
├── Coordinates specialized agents
├── Manages quality gates
└── Handles completion/escalation
```

**Implementation**:
- Commands invoke agents through Task calls
- State management delegated to MCP Server
- Business logic contained within specialized agents
- Commands handle only coordination and error escalation

**Benefits**:
- Clear separation of concerns
- Reusable agent components
- Predictable failure modes
- Simplified testing and debugging

**Anti-Pattern**: Commands that contain business logic or attempt to perform multiple specialized functions.

### 2. Quality-Driven Refinement Architecture

**Principle**: Every workflow stage must have measurable quality criteria and automatic improvement cycles.

**Pattern**:
```text
Producer Agent → Content → Critic Agent → Score → MCP Decision
     ↑                                                    ↓
     └────── Refinement Loop ←─── "refine" ←──────────────┘
```

**Implementation**:
- Producer agents generate content
- Critic agents evaluate against FSDD framework (12-point quality assessment)
- MCP Server makes objective decisions based on numerical scores
- Automatic termination when quality threshold reached (85%+)
- Stagnation detection prevents infinite loops

**Key Components**:
- **Quality Thresholds**: Configurable via environment variables
- **Stagnation Detection**: 2 consecutive iterations below 5-point improvement
- **Escalation Strategy**: User input requested when AI reaches limits

**Benefits**:
- Objective quality assessment
- Consistent improvement cycles
- Automatic termination conditions
- Predictable behavior across workflows

### 3. Dynamic Template Generation with Platform Tool Injection

**Pattern**: Create templates as functions that receive platform tool dataclasses and inject tools via string interpolation.

**Actual Implementation Pattern** (from `services/platform/templates/commands/spec_command.py`):
```python
from services.platform.models import SpecCommandTools

def generate_spec_command_template(tools: SpecCommandTools) -> str:
    return f"""---
allowed-tools:
{tools.tools_yaml}
argument-hint: [optional: technical-focus-area]
description: Transform strategic plans into detailed technical specifications
---

# /specter-spec Command: Technical Specification Creation

## Step 1: Initialize Technical Design Process
mcp__specter__initialize_refinement_loop:
  loop_type: "spec"

## Step 2: Launch Architecture Development
Invoke the spec-architect agent with this input:
Strategic Plan Summary: ${{STRATEGIC_PLAN_SUMMARY}}
Expected Output Format:
- Technical specification in markdown format
- Research Requirements section

## Step 3: Quality Assessment Loop
Invoke the spec-critic agent with this input:
${{CURRENT_SPECIFICATION}}
Expected Output Format:
- Overall Quality Score: [0-100 numerical value]
- Priority Improvements: [List of suggestions]

## Step 5: Specification Storage
Use {tools.create_spec_tool} to store the technical specification:
Title: Technical Specification: [Project Name]
Content: [Complete specification with research requirements]
"""
```

**Tool Dataclass Structure**:
The `SpecCommandTools` dataclass contains:
- `tools_yaml`: Complete YAML-formatted tools list for frontmatter
- `create_spec_tool`: Platform-specific creation tool name
- `get_spec_tool`: Platform-specific retrieval tool name
- `update_spec_tool`: Platform-specific update tool name

**Platform Abstraction**:
Platform mapping and tool selection happens in platform service layer, not in template functions. Templates receive pre-configured dataclass instances.

**Benefits**:
- Single template function generates platform-specific commands
- Tools injected based on target platform (Linear/GitHub/Markdown)
- Consistent command logic with platform-appropriate tool usage
- Easy platform addition through tool mapping updates

### 4. Template Purity and Architectural Boundaries

**Principle**: Templates must maintain strict separation between orchestration logic and implementation details.

**Template Purity Standards**:

**✅ Templates MUST**:
- Accept only abstract tool names as parameters
- Generate platform-agnostic content with tool injection points
- Contain only Main Agent coordination instructions
- Specify input formats and expected output formats for agents
- Focus solely on orchestration workflow and decision logic

**❌ Templates MUST NOT**:
- Contain platform-specific logic or constants
- Include agent behavioral instructions or implementation details
- Specify how agents should think, reason, or evaluate internally
- Mix coordination responsibilities with business logic execution
- Include default parameter values or platform assumptions

**Anti-Pattern Examples**:

```python
# ❌ WRONG: Platform logic in template
PLATFORM_TOOL_MAPPING = {...}  # Belongs in MCP server
def generate_spec_command_template(platform: str = 'linear'):  # Default values
    return f"Use {platform.title()} platform"  # Platform-specific content

# ❌ WRONG: Agent behavioral instructions
"Primary Tasks:
1. Design technical architecture based on strategic objectives
2. Analyze archive scan results for relevant existing documentation
3. Evaluate against FSDD framework (12-point quality assessment)"

# ❌ WRONG: Mixed coordination with implementation
"The spec-critic evaluates against 12 technical completeness criteria"
```

**✅ Correct Pattern**:

```python
# ✅ CORRECT: Pure template with tool injection
def generate_spec_command_template(
    create_spec_tool: str,
    get_spec_tool: str,
    update_spec_tool: str,
) -> str:
    return f"""---
allowed-tools:
  - Task(spec-architect)
  - Task(spec-critic) 
  - {create_spec_tool}
---

# Agent Invocation Pattern
Invoke the spec-architect agent with this input:
${{STRATEGIC_PLAN_SUMMARY}}

Expected Output Format:
- Technical specification in markdown format
- Research requirements section
"""

# ✅ CORRECT: Orchestration-only instructions
"Pass specification to critic agent for evaluation:
Expected Output Format:
- Overall Quality Score: [0-100 numerical value]
- Priority Improvements: [List of specific suggestions]"
```

**Project Standards Integration**:
- Reference project-specific coding standards (e.g., CLAUDE.md)
- Validate against docstring and import restrictions
- Ensure compliance with architectural separation requirements
- Verify no business logic creep into coordination templates

**Template Validation Checklist**:
1. Contains no platform detection or mapping logic
2. Specifies only input data and expected output formats
3. Includes no agent reasoning or evaluation instructions  
4. Focuses solely on Main Agent coordination workflow
5. Complies with project coding standards and restrictions

## Documentation Structure for Predictable Behavior

### 1. Standardized Agent Specification Format

**Essential Sections**:

1. **Agent Metadata**
   - Name, type, model, invocation context
   - Creates clear identity and scope

2. **Invocation Context**
   - When invoked, invocation patterns with code examples
   - Eliminates ambiguity about usage

3. **Workflow Position**
   - Visual diagrams showing agent's role in larger workflow
   - Prevents confusion about responsibilities

4. **Primary Responsibilities**
   - Numbered core tasks with clear boundaries
   - Prevents scope creep and capability drift

5. **Tool Permissions**
   - Explicitly allowed and restricted tools
   - Prevents unauthorized operations

6. **Input/Output Specifications**
   - Exact formats with examples
   - Enables reliable inter-agent communication

7. **Quality Criteria**
   - Measurable success metrics
   - Enables objective evaluation

8. **Error Handling**
   - Specific scenarios and responses
   - Ensures graceful degradation

9. **Example Interactions**
   - Concrete usage patterns
   - Reduces implementation ambiguity

### 2. Specification-Driven Behavior

**Principle**: Documentation should drive agent behavior, not describe it after the fact.

**Implementation**:
Use the [Agent Input Specification Template](../fsdd-templates/AGENT_INPUT_SPECIFICATION_TEMPLATE.md) to create clear, actionable input specifications that drive predictable agent behavior.

**Example Usage in Command Templates**:
```text
# ❌ WRONG: Includes behavioral instructions
Invoke the plan-critic agent with this context:

Strategic Plan:
${CURRENT_PLAN}

Evaluation Criteria:
- Business viability assessment  
- Market analysis completeness
- Risk identification thoroughness
Task: Evaluate the plan against FSDD framework and provide detailed feedback

# ✅ CORRECT: Input/Output specification only
Invoke the plan-critic agent with this input:
${CURRENT_PLAN}

Expected Output Format:
- Overall Quality Score: [0-100 numerical value]
- Priority Improvements: [List of specific actionable suggestions]
- Strengths: [List of well-executed areas to preserve]
```

**Benefits**:
- Predictable agent responses
- Clear expectations for integration
- Reduced debugging time
- Consistent behavior patterns

### 3. Visual Workflow Documentation

**Pattern**: Use ASCII diagrams to show data flow and agent relationships

```text
/specter-plan command → plan-generator → Strategic Plan → plan-critic
       ↑                                              ↓
       └──────────── refinement loop ←───────────────┘
```

**Benefits**:
- Immediate understanding of system architecture
- Clear handoff points between components
- Visual debugging aid
- Simplified onboarding for new developers

## Variable Management Systems

### 1. Externalized State Management

**Principle**: Workflow state should be managed by dedicated services, not individual agents.

**Implementation**:
- MCP Server manages loop state and decision logic
- Agents remain stateless and receive complete context per invocation
- State transitions handled through centralized decision engine

**Pattern**:
```text
Invoke the plan-generator agent with this context:

Context: ${CONVERSATION_CONTEXT}
Previous Feedback: ${PREVIOUS_FEEDBACK}
```

**Benefits**:
- No state synchronization issues
- Predictable agent behavior
- Easy debugging and monitoring
- Consistent decision logic

### 2. Structured Data Exchange

**Principle**: Use well-defined document formats for inter-agent communication.

**Implementation**:
- Markdown documents as primary data exchange format
- Structured sections with consistent naming
- Complete context passed in each invocation
- No shared mutable state between agents

**Format Example**:
```markdown
# Strategic Plan: [Project Name]

## Executive Summary
[High-level overview]

## Business Objectives
- [Objective 1]
- [Objective 2]

## Success Criteria
[Measurable outcomes]
```

**Benefits**:
- Human-readable intermediate outputs
- Clear data contracts between agents
- Easy debugging and validation
- Maintains context across refinement cycles

## Error Handling Patterns for Reliability

### 1. Graceful Degradation Strategy

**Principle**: System should provide best available service even when components fail.

**Implementation**:
```text
If MCP Server unavailable:
- Continue with direct agent coordination
- Display warning about degraded functionality

If critic agent unavailable:
- Proceed with generator output only
- Skip quality assessment loop

Always provide best available output with warnings
```

**Benefits**:
- System remains functional during partial failures
- Users get value even in degraded scenarios
- Prevents complete workflow failure
- Maintains user confidence

### 2. Proactive Stagnation Detection

**Principle**: Detect and handle improvement plateaus before they become infinite loops.

**Algorithm**:
```text
Stagnation Detection Logic:
1. Track quality scores across iterations
2. Calculate improvement between consecutive iterations
3. Detect stagnation when:
   - 2 consecutive improvements < 5 points
   - Quality plateau reached
4. Escalate to user input when stagnation detected
```

**Response Strategy**:
- Automatic escalation to user with specific guidance
- Clear explanation of stagnation state
- Actionable suggestions for breaking the plateau

**Benefits**:
- Prevents infinite refinement loops
- Provides user with control when AI reaches limits
- Clear feedback about system state

### 3. Standardized Error Response Format

**Pattern**:
```json
{
  "error_type": "loop_stagnation|agent_failure|mcp_error|timeout",
  "error_message": "Detailed error description",
  "recovery_action": "Specific recovery steps",
  "user_guidance": "Clear instructions for user",
  "partial_output": "Any salvageable work"
}
```

**Benefits**:
- Consistent error handling across all components
- Clear guidance for users
- Actionable recovery information
- Preserves partial work when possible

## Context Preservation in Command Templates

### Context Preservation Strategy

**Principle**: Maintain conversation and workflow context across refinement cycles.

**Implementation**:
- Complete conversation history passed to each agent invocation
- Technical assessments hidden from user interaction
- Natural dialogue flow preserved despite complex backend processing
- Context summarization to manage size constraints

**Pattern**:
```text
Context Management Structure:
- CONVERSATION_CONTEXT: Full dialogue history
- PREVIOUS_FEEDBACK: Latest critic suggestions  
- CURRENT_PLAN: Most recent generator output
- QUALITY_SCORE: Numerical assessment (0-100)
- LOOP_STATUS: Current refinement state
```

**Benefits**:
- Seamless user experience
- Consistent refinement direction
- Preserved conversation flow
- Effective context utilization

## Template Optimization Techniques

### Template Function Structure and Organization

**Pattern**: Create command templates as Python functions with consistent structure and organization.

**Static Template Function** (for commands without platform-specific tools):
```python
def generate_plan_command_template() -> str:
    return """---
allowed-tools: 
  - Task(plan-generator)
  - Task(plan-critic)
  - Task(plan-analyst)
  - Bash(~/.claude/scripts/detect-packages.sh)
argument-hint: [plan-name] [starting-prompt]
description: Create strategic plans through conversational discovery
---

# /specter-plan Command Template
[Static content - no platform-specific tools needed]
"""
```

**Directory Organization**:
```text
services/platform/templates/
├── agents/
│   ├── plan_command.py
│   ├── spec_command.py
│   └── build_command.py
├── commands/
│   └── [generated files]
└── shared/
    └── common_patterns.py
```

**YAML Frontmatter Structure**:
- `allowed-tools`: List of permitted tools and agents
- `argument-hint`: Expected parameter format
- `description`: Clear purpose statement

**Benefits**:
- Programmatic generation enables customization
- Clear separation between templates and generated files
- Consistent metadata structure across all commands
- Easy validation of command requirements
- Self-documenting command capabilities

## Template Development Workflow

### Pre-Template Development Checklist

Before creating a new command template, validate these architectural requirements:

1. **Orchestration Scope Definition**
   - [ ] Main Agent responsibilities clearly identified  
   - [ ] Required specialized agents determined
   - [ ] MCP tool integration points planned
   - [ ] No business logic assigned to Main Agent

2. **Input/Output Contract Design**
   - [ ] Agent input formats specified (data only)
   - [ ] Expected output formats defined (structure only)  
   - [ ] Context variable population sources identified
   - [ ] No agent behavioral instructions included

3. **Quality Framework Planning**
   - [ ] Success criteria measurable and objective
   - [ ] Quality thresholds established (e.g., 85%)
   - [ ] Refinement loop termination conditions defined
   - [ ] Error handling and escalation paths planned

4. **Platform Abstraction Verification**
   - [ ] Template accepts abstract tool names only
   - [ ] No platform-specific logic or constants
   - [ ] Content remains platform-agnostic
   - [ ] Tool injection points properly marked

### Template Content Structure Standards

**Required Template Sections** (in order):

1. **YAML Frontmatter**
   ```yaml
   allowed-tools:
   {tools.tools_yaml}
   argument-hint: [expected parameters]
   description: [platform-agnostic purpose]
   ```

   **Note**: The `{tools.tools_yaml}` placeholder is replaced with complete formatted tools list at generation time from the `SpecCommandTools` dataclass. Individual tools are injected as `{tools.create_spec_tool}` within template content.

2. **Orchestration Steps**
   - Sequential workflow with clear handoffs
   - Input specifications for each agent/tool
   - Expected output formats (no behavioral instructions)
   - Context variable population instructions

3. **Decision Logic**
   - MCP tool invocation patterns
   - Conditional workflow branches  
   - Error handling and recovery actions
   - User escalation scenarios

4. **Expected Outputs**
   - Final deliverable structure
   - Success criteria and metrics
   - Integration points for next phase

### Template Validation Process

**Architecture Compliance Verification**:

1. **Orchestration Boundary Check**
   - Template contains zero agent behavioral instructions
   - All agent invocations specify input data and expected output only
   - No specifications of how agents should think or evaluate
   - Main Agent coordinates but never executes business logic

2. **Platform Purity Validation**
   - No platform detection or mapping logic
   - No default parameter values or assumptions  
   - Tool names properly abstracted through parameters
   - Content descriptions platform-agnostic

3. **Project Standards Integration**
   - Compliance with coding standards (e.g., CLAUDE.md)
   - No inappropriate docstrings or comments
   - Proper import management (avoid unused imports)
   - Error handling follows established patterns

**Quality Assurance Checklist**:
- [ ] Template generates predictable command behavior
- [ ] All context variables have clear population sources
- [ ] Error scenarios include specific recovery actions
- [ ] Agent invocations follow input/output pattern consistently
- [ ] No mixed coordination and implementation responsibilities

### Common Pitfall Prevention

**Critical Violations to Avoid**:

1. **Agent Behavioral Instructions**
   ```text
   # ❌ WRONG
   "Primary Tasks:
   1. Analyze the strategic plan for technical feasibility
   2. Evaluate market conditions and competitive landscape  
   3. Identify potential risks and mitigation strategies"
   
   # ✅ CORRECT  
   "Expected Output Format:
   - Technical feasibility assessment
   - Market analysis summary
   - Risk identification with mitigation recommendations"
   ```

2. **Platform Logic in Templates**
   ```python
   # ❌ WRONG
   if platform == 'linear':
       return "Use Linear issue creation"
       
   # ✅ CORRECT
   return f"Use {create_spec_tool} to store specification"
   ```

3. **Mixed Orchestration and Implementation**
   ```text
   # ❌ WRONG
   "The spec-critic evaluates against 12 technical completeness criteria, 
   providing objective scoring for architecture and design decisions"
   
   # ✅ CORRECT
   "Quality evaluation performed by spec-critic agent using established 
   framework with 85% threshold for completion"
   ```

## Implementation Guidelines

### For Command Development

1. **Start with Orchestration Pattern**
   - Define main command as coordinator only
   - Identify required specialized agents
   - Plan MCP tool integration points
   - **Validate template purity**: No platform logic, behavioral instructions, or business logic

2. **Design Quality Framework First**
   - Define measurable success criteria
   - Create critic agent for assessment
   - Establish quality thresholds and refinement loops
   - **Ensure input/output focus**: Specify data formats, not agent reasoning processes

3. **Implement Graceful Degradation**
   - Plan for component failures
   - Design fallback behaviors
   - Provide partial value when possible
   - **Maintain orchestration boundaries**: Error handling stays in Main Agent coordination

4. **Document Before Implementation**
   - Create detailed specifications for all agents
   - Define input/output formats with examples
   - Document error scenarios and responses
   - **Verify architectural compliance**: Use Template Validation Checklist

### Template-Specific Development Guidelines

1. **Template Content Creation**
   - Focus on workflow orchestration steps only
   - Specify agent inputs as data structures
   - Define expected outputs as format specifications  
   - Include context variable population instructions
   - Add MCP tool invocation patterns with parameters

2. **Architectural Boundary Enforcement**
   - Remove any agent behavioral or reasoning instructions
   - Eliminate platform-specific logic or references
   - Extract business logic to specialized agent specifications
   - Maintain clean separation between coordination and execution

3. **Quality Assurance Integration**
   - Include objective success criteria (numerical thresholds)
   - Specify error handling with recovery actions
   - Define user escalation scenarios and guidance
   - Establish refinement loop termination conditions

4. **Project Standards Compliance**
   - Follow project-specific coding standards (CLAUDE.md)
   - Avoid inappropriate docstrings or comments
   - Use proper import management (no unused imports)
   - Implement standardized error response formats

## Success Metrics and Validation

### Quality Indicators

1. **Command Reliability**
   - Completion rate >95%
   - User escalation rate <20%
   - Average iterations to completion ≤3

2. **Agent Consistency**
   - Predictable responses to same inputs
   - Quality score variance <10%
   - Error rate <5%

3. **Documentation Effectiveness**
   - Implementation matches specification
   - Error scenarios properly handled
   - User understanding rate >90%

## Conclusion

The `/specter-plan` command development process revealed that successful multi-agent workflow systems require:

1. **Clear Architecture**: Commands as orchestrators with specialized agents
2. **Quality-Driven Development**: Measurable criteria and automatic refinement
3. **Robust Documentation**: Specifications that drive predictable behavior
4. **Reliable State Management**: Externalized state with stateless agents
5. **Graceful Error Handling**: Proactive failure detection and recovery
6. **Template Optimization**: Dynamic generation with scope isolation

These patterns provide a foundation for creating reliable, maintainable, and extensible command systems that can evolve with changing requirements while maintaining consistent quality and user experience.

## Related Documentation

- [/specter-plan Command Specification](commands/specter-plan.md) - Complete command specification
- [MCP Tools Specification](MCP_TOOLS_SPECIFICATION.md) - Loop state management tools
- [Architecture Guide](ARCHITECTURE.md) - System architecture overview
- [Agent Development Guidelines](AGENT_DEVELOPMENT_GUIDELINES.md) - Agent creation standards
