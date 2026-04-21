# Agent Development Guidelines: Phase-Driven Workflow System

## Executive Summary

This document establishes architectural patterns and development standards for creating specialized agents within the Phase-Driven Development workflow system. Through analysis of system architecture, command development lessons, and Claude Code subagent best practices, we define clear boundaries, responsibilities, and implementation patterns that ensure agent reliability, maintainability, and predictable behavior.

These guidelines focus on the four core agent concerns: inputs, tools, imperative behavior instructions, and outputs - with strict boundaries preventing external context pollution.

## Agent Architecture Foundation

### 1. Agent Isolation Principle

**Principle**: Agents operate as completely isolated processing units with no awareness of external system architecture.

**Core Isolation Requirements**:
- No knowledge of other agents or their capabilities
- No references to workflow orchestration logic
- No assumptions about platform implementations
- No awareness of refinement loops or quality gates
- No understanding of template systems or MCP tools

**Implementation Pattern** (based on actual agent templates):
```markdown
---
name: respec-phase-architect
description: Design technical architecture from strategic plans
model: sonnet
tools: Read, Bash, Grep, Glob
---

You are a technical architecture specialist focused on system design.

INPUTS: Strategic plan document in markdown format

TASKS:
1. Read and analyze strategic plan completely
2. Identify technical requirements and constraints
3. Design system architecture and component relationships
4. Create comprehensive technical specification

OUTPUTS: Technical specification in structured markdown format with:
- System architecture overview
- Component specifications
- Research requirements section
- Implementation guidelines
```

**Note**: Agent names use `respec-*` prefix for consistency.

**CRITICAL FORMATTING RULE**: Tools must be **comma-separated on a single line**. YAML array format (with `-` prefix) is **NOT supported**.

**Correct tools format**:
```yaml
tools: tool1, tool2, tool3
```

**Incorrect format** (DO NOT USE):
```yaml
tools:
  - tool1
  - tool2
  - tool3
```

**Anti-Pattern**: Agents that reference external systems:
```markdown
# ❌ WRONG: References external system knowledge
"Coordinate with the plan-critic agent to ensure quality thresholds"
"Use the MCP Server for loop state management"
"This agent works as part of the refinement cycle"
```

### 2. Single-Responsibility Agent Design

**Principle**: Each agent handles exactly one specialized function within clear behavioral boundaries.

**Responsibility Mapping**:

| Agent Type | Single Responsibility | Input Focus | Output Focus |
|-----------|---------------------|-------------|--------------|
| **Generators** | Content creation | Context + requirements | Structured documents |
| **Critics** | Quality assessment | Content for evaluation | Numerical scores + feedback |
| **Analysts** | Information extraction | Raw data/documents | Structured analysis |
| **Architects** | System design | Requirements | Technical specifications |
| **Planners** | Implementation planning | Specifications + codebase | Detailed roadmaps |
| **Coders** | Code implementation | Plans + specifications | Working code |
| **Reviewers** | Code validation | Implementation + tests | Quality assessments |

**Pattern Example - Generator Agent**:
```markdown
---
name: respec-plan-generator
description: Generate strategic plans through conversational discovery
tools: None
---

You are a strategic planning specialist focused on requirements discovery.

INPUTS: 
- Plan context and business objectives
- Previous conversation history (if refinement cycle)
- User feedback and clarifications

TASKS:
1. Conduct natural language requirements gathering
2. Extract business objectives and constraints  
3. Identify success criteria and metrics
4. Structure findings into strategic plan format

OUTPUTS: Strategic plan document containing:
- Executive summary with clear business objectives
- Detailed requirements and constraints
- Success criteria and measurable outcomes  
- Technology considerations
```

**Pattern Example - Critic Agent**:
```markdown
---
name: respec-phase-critic
description: Evaluate technical specifications against quality criteria
tools:
  - mcp__respec-ai__get_phase_markdown
  - mcp__respec-ai__store_critic_feedback
---

You are a technical specification quality specialist.

INPUTS: Loop ID for specification retrieval and feedback storage
- Loop ID provided by Main Agent for MCP operations
- Use mcp__respec-ai__get_phase_markdown(loop_id) to retrieve specification
- Evaluate complete technical specification from MCP storage

TASKS:
1. Retrieve specification using mcp__respec-ai__get_phase_markdown(loop_id)
2. Evaluate specification against FSDD quality framework
3. Assess technical completeness and clarity
4. Identify gaps and improvement opportunities
5. Calculate numerical quality score (0-100)
6. Store feedback using mcp__respec-ai__store_critic_feedback(loop_id, feedback_markdown)

OUTPUTS: Quality assessment containing:
- Overall Quality Score: [numerical value 0-100]
- Priority Improvements: [specific actionable suggestions]
- Strengths: [well-executed areas to preserve]
- Technical Concerns: [potential implementation risks]
```

**Note**: Critic agents receive `loop_id` as input and retrieve content via MCP, then store feedback directly via MCP tools. They do NOT receive markdown content as direct input.

### 3. Input-Output Contract Specification

**Principle**: Internal agent contracts must distinguish true invocation inputs from retrieved context and derived state.

**Rule of Thumb**:
- If the orchestrator passes it directly, document it in the invocation contract.
- If the agent retrieves it itself, document it as retrieved context.
- If it is normalized or derived after invocation, do **not** present it as an input.

**Preferred Internal Contract Format**:
```markdown
## Invocation Contract

### Scalar Inputs
- [deterministic scalar input]
- [deterministic scalar input]

### Grouped Markdown Inputs
- [grouped markdown payload name with exact heading schema]
- None

### Retrieved Context (Not Invocation Inputs)
- [document retrieved by MCP or filesystem read]
- [prior feedback or loop state]
```

**Scalar Input Standards**:
- Use scalar inputs for deterministic identifiers and mode flags.
- Examples:
  - `loop_id`
  - `plan_name`
  - `phase_name`
  - `phase2_mode`
  - `validation_mode`

**Grouped Markdown Input Standards**:
- Use grouped markdown payloads for variable-length internal context that would be brittle as flat parameters.
- Keep the schema heading-driven and explicit.
- Prefer markdown over JSON/YAML for prompt readability and maintainability.

**Current Standard Payload Shapes**:
```markdown
workflow_guidance_markdown
- ## Workflow Guidance
- ### Guidance Summary
- ### Constraints
- ### Resume Context
- ### Settled Decisions

project_config_context_markdown
- ## Project Config Context
- ### Stack Config TOML
- ### Language Config TOMLs
- ### Standards Guide Markdown

reference_context_markdown
- ## Reference Context
- ### Research File Paths
- ### Implementation Plan Paths
- ### Structured References

review_scope_markdown
- ## Review Scope
- ### Active Reviewers
- ### Workflow Guidance
```

**User-Facing Skill / Command Boundary**:
- User-facing Skills and commands stay free-form and natural-language-first.
- Users should **not** be required to author markdown payloads.
- Commands/skills may accept raw trailing text, clarify ambiguity, and normalize it before invoking internal agents.
- Only internal command-to-agent invocations should use grouped markdown payloads.

**Anti-Pattern**:
```markdown
INPUTS:
- request_text
- change_description
- optional_context
```

This is brittle when multiple fields are variable-length or one field is derived from another. Normalize first in the command, then pass one clear internal contract to the agent.

## Agent Behavioral Standards

### 1. Imperative Instruction Patterns

**Principle**: Agent behavior defined through direct imperatives, not explanatory descriptions.

**✅ Correct Imperative Patterns**:
```markdown
TASKS:
1. Read strategic plan document completely  
2. Extract all technical requirements and constraints
3. Design system architecture addressing requirements
4. Create specification with mandatory sections listed below
5. Include research requirements for unknown technologies
```

**❌ Incorrect Behavioral Descriptions**:
```markdown
# WRONG: Explanatory descriptions instead of imperatives
"You will analyze strategic plans to understand requirements"
"Your role is to evaluate technical feasibility" 
"You should consider best practices when designing"
```

**✅ Correct Decision Logic**:
```markdown
DECISION CRITERIA:
- If plan mentions multiple technologies: classify as "Integration Research"
- If plan mentions single technology: classify as "Individual Research"  
- If plan lacks technical details: request clarification from input
- If requirements unclear: document assumptions explicitly
```

**❌ Incorrect Process Explanations**:
```markdown
# WRONG: Process explanations instead of clear decision logic
"Consider whether the plan requires complex integration analysis"
"Think about the best approach for handling technical requirements"
```

### 2. Tool Permission Boundaries

**Principle**: Agents receive only tools essential for their specific function.

**Tool Allocation by Agent Type**:

**Critic Agents** (with MCP retrieval and storage):
```markdown
tools: mcp__respec-ai__get_plan_markdown, mcp__respec-ai__store_critic_feedback
# Use for: plan-critic, roadmap-critic evaluating via MCP
```

**Content Generation Agents**:
```markdown
tools: Read, Bash
# Use for: architects, planners (input-only + research via best-practices-rag CLI)
```

**Implementation Agents**:
```markdown
tools: Read, Edit, Write, Bash
# Use for: coders, build agents
```

**Phase Creation Agents** (with platform integration):
```markdown
tools: mcp__respec-ai__get_roadmap, mcp__respec-ai__store_phase, {tools.create_phase_tool}, {tools.update_phase_tool}
# Use for: create-phase agents with dual storage (MCP + platform)
```

### Platform Tool Usage Pattern

**Important**: When agents use platform-specific tools (like `Write`, `Read`, `Edit` for Markdown or Linear/GitHub API tools), there are two forms:

**1. Permission Form** (in frontmatter `tools:` list):
- Uses wildcards: `Write(.respec-ai/plans/*/phases/*.md)`
- Defines what file paths the agent is ALLOWED to access
- Referenced as `{tools.create_phase_tool}` in frontmatter

**2. Invocation Form** (in workflow instructions):
- Uses placeholders: `Write(.respec-ai/plans/{plan_name}/phases/{phase_name}.md)`
- Shows actual usage pattern with named parameter placeholders
- Accessed via `{tools.create_phase_tool_interpolated}` computed field from AgentTools model

**Example from create-phase agent:**

Frontmatter:
```yaml
tools: mcp__respec-ai__store_phase, {tools.create_phase_tool}
# Markdown permission: Write(.respec-ai/plans/*/phases/*.md)
# Linear permission: mcp__linear-server__create_issue(*)
```

Workflow Instructions:
```markdown
STEP 4: Store to Platform
CALL {tools.create_phase_tool_interpolated}

# Markdown actual usage: Write(.respec-ai/plans/{plan_name}/phases/{phase_name}.md, phase_markdown)
# Linear actual usage: mcp__linear-server__create_issue(project={plan_name}, title={phase_name}, ...)
```

**Why Two Forms?**
- **Wildcards** enable permission validation (Claude Code checks agent can access those paths)
- **Placeholders** show agents how to substitute actual runtime values
- **Computed fields** in AgentTools models provide the `_interpolated` versions automatically

**✅ Correct Tool Boundaries** (actual patterns from codebase):
```markdown
---
name: respec-plan-critic
tools: mcp__respec-ai__get_plan_markdown, mcp__respec-ai__store_critic_feedback
---

---
name: respec-create-phase
tools: mcp__respec-ai__get_roadmap, mcp__respec-ai__store_phase, {tools.create_phase_tool}, {tools.update_phase_tool}
---
```

**❌ Incorrect Tool Over-Allocation**:
```markdown
---
name: respec-phase-critic  # Quality evaluation agent
tools: Read, Edit, Write, Bash  # ❌ Can modify files during evaluation
---
```

### 3. Context Isolation Standards

**Principle**: Agents operate without knowledge of system context beyond their immediate inputs.

**Isolation Requirements**:
- No references to other agents or their capabilities
- No knowledge of workflow stages or phases  
- No awareness of platform implementations (Linear/GitHub/Markdown)
- No understanding of quality gate thresholds or decisions
- No assumptions about loop state or iteration counts

**✅ Correct Context Isolation**:
```markdown
You are a technical architecture specialist.

INPUTS: Strategic plan document provided as input
TASKS: Design system architecture based on plan requirements
OUTPUTS: Technical specification in structured format
```

**❌ Incorrect External References**:
```markdown
# ❌ WRONG: References external workflow knowledge
"After the plan-critic validates the plan quality..."
"This specification will be used by the taskner agent..."  
"Ensure compatibility with the Linear platform storage..."
"Consider the 85% quality threshold for progression..."
```

## Context Optimization and Data Retrieval Patterns

### Overview

**Problem**: AI agent context windows are limited and expensive. Traditional orchestration patterns where command agents retrieve documents from MCP and pass them as parameters to specialized agents create excessive context consumption.

**Impact**: In a 5-iteration MCP-driven refinement loop, traditional patterns consume ~22,000 characters in the command agent through repeated document retrieval for parameter passing, validation, and score extraction.

**Solution**: Direct MCP access pattern where specialized agents retrieve their own data using `loop_id` instead of receiving it from command agents.

**Key Principle**: Commands orchestrate control flow, not data flow. Data flows directly between MCP Server and specialized agents.

**Scope**: This pattern applies to MCP-driven refinement loops (phase, task workflows). Main Agent driven workflows (plan workflow) manage user interaction differently and do not use this pattern.

### Traditional vs Optimized Architecture

#### Traditional Pattern (Context-Heavy)

In traditional orchestration, the command agent acts as a data intermediary:

```text
Command Agent                            Specialized Agent               MCP Server
     |                                           |                           |
     |--- retrieve feedback (2k chars) -------→  |                           |
     |                                           |                           |
     |--- pass feedback as parameter ---------→  |                           |
     |                                           |                           |
     | ←- receive brief status ------------------|                           |
     |                                           |                           |
     |--- retrieve feedback again (2k chars) -→  |                           |
     |--- extract score manually -------------→  |                           |
     |                                           |                           |
     |--- retrieve feedback for validation ---→  |                           |
     |    (2k chars)                             |                           |

Total Command Context: ~6,000 chars per iteration × 5 iterations = 30,000+ chars
```

**Problems with Traditional Pattern:**
- Command retrieves same data multiple times
- Large documents passed as parameters
- Command performs data extraction tasks (score parsing)
- Command validates storage by re-retrieving data
- All context consumed in command agent

#### Optimized Pattern (Context-Light)

In the optimized pattern, specialized agents retrieve their own data:

```text
Command Agent                           Specialized Agent               MCP Server
     |                                          |                           |
     |--- invoke with loop_id ---------------→  |                           |
     |                                          |--- retrieve feedback --→  |
     |                                          |    using loop_id          |
     |                                          |← feedback (2k chars) -----|
     |                                          |                           |
     |                                          |--- retrieve phase ------→ |
     |                                          |← phase data --------------|
     |                                          |                           |
     |                                          |--- process & store -----→ |
     | ←- receive brief status -----------------|                           |
     |                                          |                           |
     |--- check MCP decision (50 chars) -----→  |                           |
     | ←- decision status (REFINE/COMPLETE) ----|                           |

Total Command Context: ~50 chars per iteration × 5 iterations = 250 chars
Agent Context: ~2,000 chars × 4 refinement iterations = 8,000 chars
System Total: 8,250 chars (63% reduction from traditional 22,000+ chars)
```

**Benefits of Optimized Pattern:**
- Command only checks control flow decisions
- Agents retrieve exactly what they need when they need it
- No large documents passed as parameters
- MCP Server handles all data operations
- Context distributed appropriately (heavy in agents, light in commands)

### Responsibility Distribution

| Concern | Command Agent | Specialized Agent | MCP Server |
|---------|--------------|-------------------|------------|
| **Control Flow** | ✅ Orchestrates workflow steps | ❌ No workflow knowledge | ✅ Provides decision status |
| **Data Retrieval** | ❌ Only for USER_INPUT display | ✅ Retrieves own data using loop_id | ✅ Stores all workflow state |
| **Data Processing** | ❌ No data transformation | ✅ Processes and generates content | ❌ Storage only |
| **Data Storage** | ❌ Never stores data | ✅ Stores results via MCP tools | ✅ Persists all state |
| **Decision Logic** | ❌ Only executes decisions | ❌ No decision authority | ✅ Calculates loop decisions |
| **Context Usage** | ✅ Minimal (50-250 chars) | ✅ Moderate (task-specific) | ❌ No context consumed |

### Implementation Guidelines

#### Agent Design Pattern

When designing agents that participate in MCP-driven refinement loops:

**✅ CORRECT: Agent retrieves own data using loop_id**

```markdown
## Invocation Contract

### Scalar Inputs
- loop_id: Refinement loop identifier for this session

### Grouped Markdown Inputs
- None

### Retrieved Context (Not Invocation Inputs)
- Previous feedback from MCP
- Current specification from MCP

STEP 0: Retrieve Previous Feedback (if refinement iteration)
CALL mcp__respec-ai__get_loop_status(loop_id=loop_id)
→ Store: LOOP_STATUS

IF LOOP_STATUS.iteration > 1:
  CALL mcp__respec-ai__get_feedback(loop_id=loop_id, count=1)
  → Store: PREVIOUS_FEEDBACK
ELSE:
  → Set: PREVIOUS_FEEDBACK = None

STEP 1: Retrieve Current Specification
CALL mcp__respec-ai__get_phase_markdown(loop_id=loop_id)
→ Store: CURRENT_PHASES

STEP 2: Process Using Retrieved Data
Use PREVIOUS_FEEDBACK and CURRENT_PHASES to generate improvements
```

**❌ WRONG: Agent receives retrieved data as parameters**

```markdown
INPUTS:
- loop_id: Loop identifier
- previous_feedback: Critic feedback from last iteration  # ❌ Retrieved context, not invocation input
- current_phase: Specification to improve                 # ❌ Retrieved context, not invocation input
```

#### Command Design Pattern

When designing commands that orchestrate MCP-driven refinement loops:

**✅ CORRECT: Command only checks decisions, retrieves for display, and normalizes internal payloads**

```markdown
STEP 5: Invoke Specialized Agent
CALL respec-phase-architect
Input:
  - loop_id: LOOP_ID
  - plan_name: PLAN_NAME
  - phase_name: PHASE_NAME
  - optional_instructions: OPTIONAL_INSTRUCTIONS
  # NO feedback parameter - architect retrieves from MCP itself

STEP 6: Get Loop Decision
LOOP_DECISION = mcp__respec-ai__decide_loop_next_action(loop_id=LOOP_ID)
# Returns: {status: "COMPLETE|REFINE|USER_INPUT"}
# No feedback retrieval - MCP handles internally

STEP 7: Handle Decisions
IF LOOP_DECISION == "REFINE":
  Display: "⟳ Refining - architect will address feedback"
  Return to Step 5

IF LOOP_DECISION == "USER_INPUT":
  # ONLY NOW retrieve feedback for user display
  FEEDBACK = mcp__respec-ai__get_feedback(loop_id=LOOP_ID, count=1)
  Display: FEEDBACK to user
  Prompt user for input
```

For richer internal guidance:

```markdown
WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:
  ## Workflow Guidance
  ### Guidance Summary
  [...]
  ### Constraints
  [...]
  ### Resume Context
  [...]
  ### Settled Decisions
  [...]

CALL respec-coder
Input:
  - coding_loop_id: CODING_LOOP_ID
  - task_loop_id: TASK_LOOP_ID
  - plan_name: PLAN_NAME
  - phase_name: PHASE_NAME
  - mode: None
  - workflow_guidance_markdown: WORKFLOW_GUIDANCE_MARKDOWN
  - project_config_context_markdown: PROJECT_CONFIG_CONTEXT_MARKDOWN
```

**Narrow Exception: Commit Metadata Synthesis in `respec-code` / `respec-patch`**

For commit-lifecycle orchestration, `respec-code` and `respec-patch` may retrieve the latest
feedback outside `USER_INPUT` to synthesize command-owned commit metadata (subject/summary/score).

Exception constraints:
- Retrieval is read-only and limited to latest feedback needed for commit message composition.
- Retrieved feedback is NOT passed to specialized agents as input parameters.
- Retrieval does NOT override MCP decision authority (`decide_loop_next_action` remains source of truth).
- Commands continue to own control flow; agents continue to retrieve their own processing context.

**❌ WRONG: Command retrieves data for agents**

```markdown
STEP 5a: Retrieve Feedback for Agent
CRITIC_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=LOOP_ID, count=2)  # ❌ Unnecessary

STEP 5b: Invoke Agent with Feedback
CALL respec-phase-architect
Input:
  - previous_feedback: CRITIC_FEEDBACK  # ❌ Don't pass large documents

STEP 6: Retrieve Feedback Again for Validation
STORED_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=LOOP_ID, count=1)  # ❌ Duplicate retrieval
```

### Example: phase Workflow Implementation

This section demonstrates the context optimization pattern using real examples from the phase workflow implementation.

#### Command Implementation (spec_command.py)

**Step 5: Invoke phase-architect**

The command invokes the phase-architect agent with only the `loop_id` and essential context parameters. No feedback is passed as a parameter - the agent retrieves it directly from MCP.

```markdown
STEP 5: Phase Refinement

Invoke: respec-phase-architect
Input:
  - loop_id: LOOP_ID
  - plan_name: PLAN_NAME
  - phase_name: PHASE_NAME
  - strategic_plan_summary: STRATEGIC_PLAN_SUMMARY
  - optional_instructions: USER_INSTRUCTIONS (if provided)
  - kb_query_results: KB_RESULTS (from best-practices-rag query-kb)

Agent will:
1. Retrieve current phase from MCP using loop_id
2. Retrieve previous critic feedback from MCP (if iteration > 1)
3. Refine phase based on strategic plan, feedback, and KB insights
4. Store updated phase to MCP

No feedback passed as parameter - architect retrieves directly from MCP.
```

**Step 6: Get Loop Decision**

The command checks only the loop decision status, not the feedback itself. The MCP Server handles score calculation and decision logic internally.

```markdown
STEP 6: Decision Point

#### Step 6b: Get Loop Decision
LOOP_DECISION_RESPONSE = mcp__respec-ai__decide_loop_next_action(loop_id=LOOP_ID)
LOOP_DECISION = LOOP_DECISION_RESPONSE.status

Note: No need to retrieve feedback or score - MCP handles internally.
Decision options: "COMPLETE", "REFINE", "USER_INPUT"
```

**Step 7: Handle Decisions**

The command only retrieves feedback when USER_INPUT is required - for display to the user. In all other cases, feedback remains in MCP and is accessed directly by the phase-architect agent.

```markdown
STEP 7: Execute Decision

#### If LOOP_DECISION == "REFINE"
Display: "⟳ Refining specification - phase-architect will address critic feedback"
Return to Step 5 (phase-architect will retrieve feedback from MCP itself)

#### If LOOP_DECISION == "USER_INPUT"
Display: "⚠ Quality improvements needed - user input required"

# ONLY NOW retrieve feedback for user display
LATEST_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=LOOP_ID, count=1)

Display to user:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITIC FEEDBACK - USER INPUT REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{LATEST_FEEDBACK.message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prompt: "Please provide guidance to improve the specification:"
Store user input and return to Step 5
```

#### Agent Implementation (spec_architect.py)

**STEP 0: Retrieve Feedback**

The phase-architect agent checks the iteration number to determine if previous feedback exists, then retrieves it directly from MCP using the `loop_id`. This eliminates the need for the command to pass feedback as a parameter.

```markdown
STEP 0: Retrieve Previous Critic Feedback (if refinement iteration)
→ Check if this is a refinement by getting loop status
CALL mcp__respec-ai__get_loop_status(loop_id=loop_id)
→ Store: LOOP_STATUS

IF LOOP_STATUS.iteration > 1:
  → This is a refinement iteration - retrieve previous critic feedback
  CALL mcp__respec-ai__get_feedback(loop_id=loop_id, count=1)
  → Store: PREVIOUS_FEEDBACK
  → Extract key improvement areas from feedback for use in STEP 2
ELSE:
  → First iteration (or iteration 1) - no previous feedback exists
  → Set: PREVIOUS_FEEDBACK = None
```

**STEP 1: Retrieve Specification**

The agent retrieves the current specification from MCP using `loop_id`, ensuring it always works with the latest version stored in MCP.

```markdown
STEP 1: Retrieve Current Specification
CALL mcp__respec-ai__get_phase_markdown(
  plan_name=None,
  phase_name=None,
  loop_id=loop_id
)
→ Verify: Specification markdown received
→ Expected error: "not found" if new phase (iteration=0)
```

**STEP 2: Use Retrieved Data**

The agent uses the feedback retrieved in STEP 0 to guide improvements. All data retrieval is self-contained within the agent.

```markdown
STEP 2: Incorporate Feedback (if refinement iteration)
IF PREVIOUS_FEEDBACK exists (from STEP 0):
  → Analyze specific issues identified by critic
  → Address ALL items in "Priority Improvements" section
  → Maintain strengths noted in feedback
  → Focus improvements on areas critic flagged as deficient
```

### Benefits and Metrics

#### Performance Benefits

**Context Window Savings:**
- Command Agent: 99% reduction (22,000 → 250 chars)
- System Total: 63% reduction (22,000 → 8,250 chars)
- Cost Reduction: Proportional to token reduction
- Speed Improvement: Less data transfer per iteration

**Iteration Breakdown (5-iteration refinement loop):**

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Command context per iteration | ~4,400 chars | ~50 chars | 99% |
| Command total (5 iterations) | ~22,000 chars | ~250 chars | 99% |
| Agent context per iteration | 0 chars | ~2,000 chars | -2,000 |
| Agent total (4 refinements) | 0 chars | ~8,000 chars | -8,000 |
| **System Total** | **22,000 chars** | **8,250 chars** | **63%** |

#### Architectural Benefits

**Separation of Concerns:**
- Commands focus on control flow orchestration
- Agents focus on specialized processing
- MCP Server acts as single source of truth
- No data intermediation by commands

**Agent Self-Sufficiency:**
- Agents retrieve exactly what they need
- No dependency on command data passing
- Agents can retry retrieval independently
- Clear ownership of data access

**Maintainability:**
- Changes to feedback structure don't affect commands
- Agent implementations can evolve independently
- No brittle parameter passing chains
- Easier to reason about data flow

#### Scalability Benefits

**Pattern Extensibility:**
- Applies to all MCP-driven refinement workflows (phase, task)
- Can add new agents without changing command patterns
- MCP Server handles complexity of state management
- Clear pattern for future agent development

### Pattern Application

#### Workflows Using This Pattern

This optimization pattern applies to **MCP-driven refinement loop workflows** only:

**phase Workflow:** ✅ Uses this pattern
- Command: `phase_command.py`
- Agents: `phase-architect` ↔ `phase-critic`
- Pattern: Architect retrieves feedback from MCP using loop_id
- Loop Driver: MCP Server (decide_loop_next_action)

**build Workflow:** ✅ Should use this pattern
- Command: `build_command.py`
- Agents: `taskner` ↔ `task-critic` (planned)
- Pattern: Planner retrieves feedback from MCP using loop_id
- Loop Driver: MCP Server (decide_loop_next_action)

**plan Workflow:** ❌ Exception - does NOT use this pattern
- Command: `plan_command.py`
- Agents: `plan-analyst` ↔ `plan-critic`
- Pattern: Main Agent driven with direct user interaction
- Loop Driver: Command Agent (not MCP loop)
- Reason: Conversational workflow requires Main Agent to manage user dialogue directly

#### When to Apply This Pattern

**✅ Use Direct MCP Access Pattern When:**
- Workflow uses MCP Server for loop control (decide_loop_next_action)
- Agent participates in MCP-driven refinement loop
- Agent needs access to workflow state stored in MCP (specs, feedback, plans)
- Agent needs to check iteration number for conditional logic
- Agent stores results back to MCP
- Command orchestrates multiple refinement iterations via MCP decisions

**❌ Don't Use This Pattern When:**
- Workflow is Main Agent driven (conversational, user-interactive)
- Command needs to manage user dialogue directly (like plan workflow)
- Agent operates on static inputs (no loop context)
- Data is small enough to pass efficiently (<500 chars)
- Agent has no access to MCP tools
- Workflow is single-iteration (no refinement)
- Loop control is handled by command agent, not MCP Server

#### Implementation Checklist

When implementing agents using this pattern:

**Agent Requirements:**
- [ ] Receives `loop_id` as input parameter
- [ ] Has MCP retrieval tools in frontmatter
- [ ] Checks iteration number via `get_loop_status(loop_id)`
- [ ] Retrieves own data using `loop_id` parameter
- [ ] Conditionally retrieves feedback (if iteration > 1)
- [ ] Stores results back to MCP using `loop_id`
- [ ] Returns brief status message only (no data payloads)

**Command Requirements:**
- [ ] Initializes refinement loop with MCP
- [ ] Invokes agents with `loop_id` only (no data parameters)
- [ ] Checks loop decision using `decide_loop_next_action(loop_id)`
- [ ] Only retrieves feedback for USER_INPUT display
- [ ] Never acts as data intermediary
- [ ] Focuses on control flow orchestration
- [ ] Uses adapter-rendered command invocation for command-to-command handoff (no ad-hoc shell command strings)
- [ ] Treats shell/Bash fallback for workflow command handoff as non-compliant
- [ ] Fails closed with structured error when required orchestration invocation path is unavailable

**MCP Server Requirements:**
- [ ] Provides loop status retrieval
- [ ] Stores all workflow state (specs, feedback, plans)
- [ ] Implements decision logic (`decide_loop_next_action`)
- [ ] Tracks iterations and scores automatically
- [ ] Returns data via loop_id queries

### Key Takeaways

**Core Principle**: In MCP-driven refinement loops, commands orchestrate control flow, not data flow. Specialized agents retrieve their own data directly from MCP Server using `loop_id`.

**Context Optimization**: This pattern reduces command agent context by 99% and total system context by 63% in MCP-driven refinement workflows (phase, task).

**Agent Self-Sufficiency**: Agents using this pattern are independent, self-sufficient processors that retrieve exactly what they need when they need it.

**Scalability**: This pattern enables sustainable growth of MCP-driven refinement workflows without exponential context consumption.

**Exception**: Main Agent driven workflows (like plan) manage user dialogue directly and do not use this pattern.

### Reference Implementation and Template Safety

#### Phase Workflow as Reference Pattern

The phase workflow demonstrates the correct context-optimized MCP-driven refinement loop pattern:
- **Command**: src/platform/templates/commands/phase_command.py
- **Architect Agent**: src/platform/templates/agents/phase_architect.py
- **Critic Agent**: src/platform/templates/agents/phase_critic.py

Use these files as the reference implementation when creating new MCP-driven workflows.

#### F-String Template Safety in Commands

Commands are Python f-strings (return f"""..."""). This creates a critical distinction between template generation time and command execution time.

**Template Generation Time** (Python scope):
- Function executes: `generate_phase_command_template(tools: PhaseCommandTools)`
- Python evaluates f-string and processes all {variable} expressions
- Available variables: tools, and any Python variables in function scope
- Output: Markdown template string stored in .claude/commands/

**Command Execution Time** (Main Agent scope):
- Main Agent reads markdown from .claude/commands/
- Main Agent executes pseudocode instructions
- Available variables: LOOP_DECISION, LATEST_FEEDBACK, PLAN_NAME (defined in pseudocode)

**The Problem**:
```python
def generate_command_template(tools):
    return f"""
    LATEST_FEEDBACK = mcp__respec-ai__get_feedback(...)  # ← Pseudocode, not Python

    Display: {LATEST_FEEDBACK.message}  # ← Python tries to evaluate this NOW!
    """
```

Python sees `{LATEST_FEEDBACK.message}` and tries to find LATEST_FEEDBACK in the Python function scope. It doesn't exist → NameError.

**Solution - Use Plain Text for Pseudocode Variables**:
```python
def generate_command_template(tools):
    return f"""
    LATEST_FEEDBACK = mcp__respec-ai__get_feedback(...)  # ← Pseudocode

    Display LATEST_FEEDBACK to user with:  # ← Plain text, no curly braces
    - Current score and iteration
    - Priority areas

    # OR use square brackets for extraction:
    Score: [Extract from LATEST_FEEDBACK]
    """
```

**Safe Patterns**:
```text
✅ LATEST_FEEDBACK = mcp__respec-ai__get_feedback(...)
✅ IF "error" in LATEST_FEEDBACK:
✅ Display LATEST_FEEDBACK to user with:
✅ [Extract score from LATEST_FEEDBACK]
✅ {tools.tool_name}  ← OK - tools is a Python variable

❌ {LATEST_FEEDBACK.message}
❌ {LOOP_DECISION}
❌ {PLAN_NAME} in pseudocode sections
```

**Detection Rule**:
If a variable in curly braces is:
- A function parameter (tools, plan_name passed to function) → ✅ Safe
- Defined in Python code above the f-string → ✅ Safe
- Defined in pseudocode/markdown instructions → ❌ Unsafe - remove braces

**Reference**: See phase_command.py lines 348-383 for correct USER_INPUT handling without f-string interpolation.

## Agent Documentation Structure

### 1. Standardized Agent Specification Format

**Required Sections** (in order):

1. **Agent Metadata** (YAML frontmatter)
2. **Agent Identity Statement**  
3. **Invocation Contract**
4. **Task Instructions** (Imperative)
5. **Output Specification**
6. **Quality Criteria** (Objective measures)

**Complete Template**:
```markdown
---
name: [agent-name]
description: [When this agent should be invoked - action-oriented]
model: [sonnet|haiku] # Optional - defaults to sonnet
tools: tool1, tool2, tool3  # Comma-separated on single line
---

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: result = tool_name(param="value")
  ❌ WRONG: <tool_name><param>value</param>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

You are a [specific role] focused on [specific function].

## Invocation Contract

### Scalar Inputs
- [required scalar input]
- [optional scalar input]

### Grouped Markdown Inputs
- [grouped payload with exact headings]
- None

### Retrieved Context (Not Invocation Inputs)
- [retrieved document or loop state]
- [retrieved document or loop state]

TASKS:
1. [Imperative action with specific objective]
2. [Imperative action with specific objective]  
3. [Imperative action with specific objective]
4. [Imperative action with specific objective]

OUTPUTS: [Structured format requirements]
- [Required element]: [format specification]
- [Required element]: [format specification]
- [Optional element]: [conditions for inclusion]

QUALITY CRITERIA:
- [Objective measure]: [specific threshold]
- [Objective measure]: [specific threshold]
```

### 2. Specification-Driven Behavior

**Principle**: Documentation drives agent behavior through explicit specifications, not process descriptions.

**✅ Correct Specification Approach**:
```markdown
## Invocation Contract

### Scalar Inputs
- [deterministic identifier]

### Grouped Markdown Inputs
- [normalized markdown payload when needed]

### Retrieved Context (Not Invocation Inputs)
- [documents the agent retrieves itself]

TASKS:
1. Read implementation plan completely
2. Implement each step in specified sequence
3. Run tests after each implementation step
4. Document results and any deviations from plan

OUTPUTS: Implementation results containing:  
- Completed code changes with file paths
- Test execution results and coverage
- Implementation notes and decisions made
- Remaining work items (if any)
```

**❌ Incorrect Process Description Approach**:
```markdown
# ❌ WRONG: Describes process instead of specifying behavior
"You will implement the plan by following best practices"
"Consider the implementation sequence when coding"  
"Use your expertise to handle any technical challenges"
```

### 3. Error Handling and Recovery Patterns

**Principle**: Agents include explicit error handling within their isolation boundaries.

**Error Handling Template**:
```markdown
ERROR HANDLING:
- If [specific error condition]: [specific recovery action]
- If [specific error condition]: [specific recovery action]
- If input format invalid: document issues and request correction
- If required tools unavailable: document limitations and partial results
- Always provide best-effort output with clear status indicators
```

**Recovery Action Standards**:
- Specific, actionable recovery steps
- Clear documentation of limitations
- Partial results preservation when possible  
- Status indicators for incomplete work
- No references to external help or escalation

**✅ Correct Error Handling**:
```markdown
ERROR HANDLING:
- If strategic plan format invalid: document structural issues and proceed with available sections
- If technical requirements unclear: document assumptions made during design
- If research script fails: proceed without external research and document limitation
- Always produce specification with clear indicators of data quality and completeness
```

## Agent Implementation Patterns

### 1. Generator Agent Pattern

**Purpose**: Create content based on requirements and context.

**Template Structure**:
```markdown
---
name: respec-[content-type]-generator
description: Generate [specific content type] from [specific input]
tools: Read  # Input-only for most generators
---

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: result = tool_name(param="value")
  ❌ WRONG: <tool_name><param>value</param>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

You are a [domain] specialist focused on [content creation type].

## Invocation Contract

### Scalar Inputs
- [primary identifier or deterministic input]

### Grouped Markdown Inputs
- [normalized grouped payload when needed]
- None

### Retrieved Context (Not Invocation Inputs)
- [primary data source if retrieved]
- [context information if retrieved]

TASKS:
1. [Content analysis imperative]
2. [Content structure imperative] 
3. [Content generation imperative]
4. [Quality assurance imperative]

OUTPUTS: [Specific content format]
- [Required section]: [content specification]
- [Required section]: [content specification]

QUALITY CRITERIA:
- [Completeness measure]: [threshold]
- [Clarity measure]: [threshold]  
```

**Example - Plan Generator**:
```markdown
---
name: respec-plan-generator
description: Generate strategic plans through conversational discovery
tools: None
---

You are a strategic planning specialist focused on requirements discovery.

INPUTS: Business context and objectives provided through conversation
- Plan goals and constraints
- User responses to clarifying questions
- Business requirements and priorities

TASKS:
1. Conduct natural language requirements gathering through questions
2. Extract core business objectives and success criteria
3. Identify constraints, resources, and timeline considerations
4. Structure findings into comprehensive strategic plan

OUTPUTS: Strategic plan document containing:
- Executive Summary: High-level project overview and objectives  
- Business Objectives: Specific, measurable goals
- Success Criteria: Quantifiable outcomes and metrics
- Constraints: Resource, time, and technical limitations
- Next Steps: Recommended actions for implementation

QUALITY CRITERIA:
- Objectives clarity: All goals clearly stated and measurable
- Requirements completeness: All stated needs addressed
- Constraint identification: Limitations explicitly documented
```

### 2. Critic Agent Pattern  

**Purpose**: Evaluate content against objective quality criteria.

**Template Structure**:
```markdown
---
name: [content-type]-critic
description: Evaluate [content type] against quality criteria
tools: mcp__respec-ai__get_[content]_markdown, mcp__respec-ai__store_critic_feedback
---

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: content = mcp__respec-ai__get_[content]_markdown(loop_id="...")
  ❌ WRONG: <mcp__respec-ai__get_[content]_markdown><loop_id>...</loop_id>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

You are a [domain] quality specialist focused on [evaluation type].

## Invocation Contract

### Scalar Inputs
- loop_id: Refinement loop identifier

### Grouped Markdown Inputs
- None

### Retrieved Context (Not Invocation Inputs)
- [Primary content] via MCP retrieval
- [Previous feedback] via MCP retrieval

TASKS:
1. [Analysis imperative using specific framework]
2. [Quality measurement imperative]
3. [Gap identification imperative] 
4. [Score calculation imperative]

OUTPUTS: Quality assessment containing:
- Overall Quality Score: [0-100 numerical value]
- Priority Improvements: [specific actionable suggestions]
- Strengths: [well-executed areas to preserve]
- [Domain-specific concerns]: [relevant risk areas]

QUALITY CRITERIA:
- Score objectivity: Based on measurable criteria only
- Improvement specificity: All suggestions include concrete actions
- Strength recognition: Positive elements clearly identified
```

**Example - Phase Critic**:
```markdown
---
name: respec-phase-critic
description: Evaluate technical specifications against quality criteria
tools: mcp__respec-ai__get_phase_markdown, mcp__respec-ai__store_critic_feedback
---

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: phase = mcp__respec-ai__get_phase_markdown(loop_id="...")
  ❌ WRONG: <mcp__respec-ai__get_phase_markdown><loop_id>...</loop_id>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

You are a technical specification quality specialist.

INPUTS: Loop ID for specification retrieval and feedback storage
- Loop ID provided by Main Agent for MCP operations
- Use mcp__respec-ai__get_phase_markdown(loop_id) to retrieve specification
- Complete technical specification retrieved from MCP storage

TASKS:
1. Retrieve specification using mcp__respec-ai__get_phase_markdown(loop_id)
2. Evaluate specification against FSDD quality framework (12-point criteria)
3. Assess technical completeness, clarity, and implementability
4. Identify gaps, inconsistencies, and improvement opportunities
5. Calculate numerical quality score based on objective criteria
6. Store feedback using mcp__respec-ai__store_critic_feedback(loop_id, feedback_markdown)

OUTPUTS: Quality assessment containing:
- Overall Quality Score: [0-100 numerical value]
- Priority Improvements: [specific technical gaps to address]
- Strengths: [well-designed areas to preserve]
- Technical Concerns: [implementation risks and challenges]

QUALITY CRITERIA:
- Score objectivity: Based on FSDD framework criteria only
- Technical accuracy: All assessments technically sound
- Improvement actionability: Each suggestion includes specific steps
```

### 3. Implementation Agent Pattern

**Purpose**: Execute implementation tasks based on specifications.

**Template Structure**:
```markdown
---
name: respec-[implementation-type]-[agent-type]
description: [Implementation function] based on [specification type]
tools: Read, Edit, Write, Bash  # Full implementation access
---

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: result = tool_name(param="value")
  ❌ WRONG: <tool_name><param>value</param>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

You are a [implementation domain] specialist focused on [execution type].

## Invocation Contract

### Scalar Inputs
- [deterministic identifiers and mode flags]

### Grouped Markdown Inputs
- [workflow guidance or config payloads]

### Retrieved Context (Not Invocation Inputs)
- [implementation plan or task document]
- [current code context]

TASKS:
1. [Implementation preparation imperative]
2. [Core implementation imperative]
3. [Validation imperative]
4. [Documentation imperative]

OUTPUTS: Implementation results containing:
- [Completed work]: [specific deliverables]
- [Validation results]: [test outcomes]  
- [Implementation notes]: [decisions and changes]
- [Status indicators]: [completion state]

QUALITY CRITERIA:
- Implementation completeness: All specified work completed
- Validation success: Tests passing and requirements met
- Documentation clarity: Changes and decisions clearly recorded
```

**Example - Build Coder**:
```markdown
---
name: respec-coder
description: Implement code based on implementation plans and specifications
tools: Read, Edit, Write, Bash
---

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: result = tool_name(param="value")
  ❌ WRONG: <tool_name><param>value</param>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

You are a software implementation specialist focused on code development.

## Invocation Contract

### Scalar Inputs
- coding_loop_id: Feedback loop identifier
- task_loop_id: Task retrieval loop identifier
- plan_name: Project name
- phase_name: Phase name
- mode: Optional scalar mode flag

### Grouped Markdown Inputs
- workflow_guidance_markdown
- project_config_context_markdown

### Retrieved Context (Not Invocation Inputs)
- Task document
- Phase document
- Current codebase context

TASKS:
1. Read implementation plan and current codebase thoroughly
2. Implement each step following Test-Driven Development approach
3. Run tests after each significant implementation step
4. Document implementation decisions and any plan deviations

OUTPUTS: Implementation results containing:
- Completed Code Changes: All modified files with clear descriptions
- Test Results: Execution outcomes and coverage reports
- Implementation Notes: Technical decisions and problem-solving approach
- Status Report: Completion indicators and remaining work items

QUALITY CRITERIA:
- Code functionality: All implemented features work as specified
- Test coverage: Comprehensive tests passing for new functionality  
- Plan adherence: Implementation follows specified roadmap
- Documentation completeness: All changes clearly documented
```

## Agent Validation and Quality Assurance

### 1. Agent Specification Validation

**Pre-Implementation Validation Checklist**:

**Isolation Boundary Check**:
- [ ] Agent contains no references to other agents or system components
- [ ] Agent has no knowledge of workflow orchestration or external context  
- [ ] Agent operates solely on provided inputs without external assumptions
- [ ] Agent produces outputs without referencing downstream consumption

**Specification Completeness Check**:
- [ ] All inputs clearly specified with format requirements
- [ ] All tasks defined as specific, actionable imperatives
- [ ] All outputs structured with required elements defined  
- [ ] Error handling included with specific recovery actions

**Tool Permission Verification**:  
- [ ] Tools limited to minimum required for agent function
- [ ] No excessive permissions for agent responsibilities
- [ ] Tool access matches agent type (read-only for critics, full for implementers)

**Behavioral Clarity Check**:
- [ ] Instructions use imperative voice for all actions
- [ ] No explanatory or descriptive behavioral guidance  
- [ ] Decision criteria explicit and objective
- [ ] Quality criteria measurable and specific

### 2. Agent Testing Patterns

**Unit Testing for Agent Specifications**:

**Input Validation Testing**:
```markdown
Test Case: Valid Input Format
- Provide correctly formatted input
- Verify agent processes input without errors
- Validate output structure matches specification

Test Case: Invalid Input Format  
- Provide malformed input
- Verify agent handles errors gracefully
- Confirm partial results with error documentation

Test Case: Missing Input Elements
- Provide incomplete input  
- Verify agent documents missing elements
- Validate agent produces best-effort output
```

**Output Quality Testing**:
```markdown
Test Case: Output Structure Validation
- Verify all required output elements present
- Confirm output format matches specification  
- Validate content quality meets criteria

Test Case: Consistency Testing
- Provide same input multiple times
- Verify consistent output structure
- Measure response variability within acceptable limits

Test Case: Edge Case Handling  
- Provide boundary condition inputs
- Verify robust error handling
- Validate meaningful outputs under stress conditions
```

### 3. Agent Performance Metrics

**Quality Indicators for Agent Specifications**:

**Specification Quality**:
- Input clarity: Users can provide correct inputs >90% of time
- Task precision: Agent behavior predictable across invocations
- Output consistency: Structure variance <10% across runs
- Error handling: Graceful degradation in >95% of failure cases

**Implementation Quality**:
- Execution success: Task completion rate >95%
- Output quality: Meets specified criteria >90% of time
- Recovery effectiveness: Error recovery success >85%
- User satisfaction: Meets user expectations >90% of cases

## Common Anti-Patterns and Violations

### 1. ❌ Context Pollution Anti-Patterns

**Problem**: Agents that reference external system knowledge.

**Violation Examples**:
```markdown
# ❌ WRONG: References other agents
"After the phase-critic validates the specification quality..."
"Coordinate with plan-generator for requirements clarity..."
"This output will be used by taskner agent..."

# ❌ WRONG: References workflow orchestration  
"As part of the refinement loop process..."
"When the MCP server decides to continue refinement..."
"During the quality gate evaluation phase..."

# ❌ WRONG: References platform implementation
"Store the specification in Linear issue format..."
"Ensure compatibility with GitHub integration..." 
"Format output for Markdown file storage..."
```

**✅ Correct Isolation Approach**:
```markdown
# ✅ CORRECT: Agent operates on inputs only
"Read the provided strategic plan document"
"Create technical specification based on input requirements"  
"Produce structured output in specified markdown format"
```

### 2. ❌ Behavioral Description Anti-Patterns

**Problem**: Explaining what agents do instead of instructing what they must do.

**Violation Examples**:
```markdown
# ❌ WRONG: Behavioral descriptions
"You will analyze strategic plans to understand technical requirements"
"Your role involves evaluating specifications for quality"
"You should consider best practices when implementing code"

# ❌ WRONG: Process explanations
"Think about the technical feasibility of requirements"
"Consider different approaches to system architecture"  
"Evaluate the plan using your expertise"
```

**✅ Correct Imperative Approach**:
```markdown  
# ✅ CORRECT: Direct imperatives
"Read strategic plan document completely"
"Extract all technical requirements and constraints"
"Design system architecture addressing each requirement"
"Create specification following structured format below"
```

### 3. ❌ Tool Over-Allocation Anti-Patterns

**Problem**: Granting unnecessary tool permissions to agents.

**Violation Examples**:
```markdown
# ❌ WRONG: Critics with modification tools
---
name: respec-phase-critic
tools:
  - Read
  - Edit
  - Write  # ❌ Can modify content during evaluation
---

# ❌ WRONG: Generators with execution tools
---
name: respec-plan-generator
tools:
  - Read
  - Bash
  - Edit
  - Write  # ❌ Excessive permissions for content generation
---
```

**✅ Correct Minimal Permission Approach**:
```markdown
# ✅ CORRECT: Critics with MCP retrieval and storage only
---
name: respec-phase-critic
tools: mcp__respec-ai__get_phase_markdown, mcp__respec-ai__store_critic_feedback
---

# ✅ CORRECT: Generators with input-only access
---
name: respec-plan-generator
tools: None  # Content generation from conversation, no file access needed
---
```

### 4. ❌ Vague Specification Anti-Patterns

**Problem**: Unclear inputs, outputs, or task definitions.

**Violation Examples**:
```markdown
# ❌ WRONG: Vague input specification
"INPUTS: Plan information and requirements"

# ❌ WRONG: Unclear task instructions
"TASKS: Analyze and improve the provided content"

# ❌ WRONG: Unstructured output specification  
"OUTPUTS: High-quality technical documentation"
```

**✅ Correct Specific Specification Approach**:
```markdown
# ✅ CORRECT: Specific input format
"INPUTS: Strategic plan document in markdown format containing:
- Executive summary with business objectives  
- Technical requirements and constraints
- Success criteria and measurable outcomes"

# ✅ CORRECT: Specific task imperatives
"TASKS:
1. Read strategic plan document completely
2. Extract technical requirements and identify missing elements
3. Design system architecture with component relationships
4. Create specification following structured template below"

# ✅ CORRECT: Structured output specification
"OUTPUTS: Technical specification containing:
- System Architecture: Component diagram and relationships
- Technical Requirements: Functional and non-functional specifications
- Research Requirements: External knowledge needs for implementation  
- Implementation Guidelines: Development approach and standards"
```

## Conclusion

The Phase-Driven Workflow system achieves reliability and maintainability through strict agent isolation, clear behavioral specifications, and minimal permission boundaries. Success depends on following these architectural patterns: single-responsibility design, imperative instruction specification, structured input/output contracts, and complete context isolation.

Agents that operate as isolated processing units with clear boundaries create predictable, testable, and maintainable workflows. By focusing solely on inputs, tools, behavior, and outputs - without external system knowledge - agents remain robust across system changes and platform evolution.

These guidelines provide the foundation for creating specialized agents that deliver consistent quality while maintaining architectural flexibility for future system enhancements.

## Review-Team Coordination Pattern

### Overview

The code review workflow uses a **review-team pattern** where multiple specialized reviewer agents
run in parallel, each producing a partial review section, with a consolidator agent merging all
sections into a single CriticFeedback document.

This pattern differs from standalone agent workflows in several ways:

### Storage: Review Sections vs CriticFeedback

**Standalone agents** (phase-architect, task-planner, plan-analyst) store complete documents or
CriticFeedback directly via `store_critic_feedback` or `store_document`.

**Review-team agents** store partial **review sections** via `store_review_section`. Each section
is stored under a unique key within the shared loop scope. Only the review-consolidator produces
the final CriticFeedback.

```text
Reviewer Agent → store_review_section(key="plan/phase/review-{slug}", content=section_markdown)
Consolidator   → list_review_sections → get_review_section (each) → store_critic_feedback (merged)
```

### Section Key Naming

Each reviewer stores its output under a unique section key following the pattern:

```text
{PLAN_NAME}/{PHASE_NAME}/review-{reviewer-slug}
```

Current section keys:

- `review-quality-check` — automated-quality-checker (core, 50 pts)
- `review-spec-alignment` — spec-alignment-reviewer (core, 50 pts)
- `review-code-quality` — code-quality-reviewer (always active, -15 to +5)
- `review-frontend` — frontend-reviewer (specialist, -10 to +5)
- `review-backend-api` — backend-api-reviewer (specialist, -10 to +5)
- `review-database` — database-reviewer (specialist, -10 to +5)
- `review-infrastructure` — infrastructure-reviewer (specialist, -10 to +5)
- `review-coding-standards` — coding-standards-reviewer (specialist, -10 to +5)

### Parallel Execution

The orchestrating command (code_command.py Step 7.4 loop) launches all Phase 1 review agents in
parallel. Each reviewer operates independently — no reviewer references or depends on another
reviewer's output. The review-consolidator runs **after** all other reviewers complete.

```text
Phase 1 Parallel:  AQC + spec-alignment + code-quality + [optional specialists]
Phase 1 Sequential: review-consolidator (merges all sections)
Phase 2 Standalone: coding-standards-reviewer (separate loop, stores CriticFeedback directly)
```

### Shared Loop ID

All Phase 1 review-team agents share the same `coding_loop_id`. Each agent uses this ID for:

- Retrieving previous feedback (progress tracking across iterations)
- Storing its review section (via the section key, not the loop ID directly)

The consolidator uses the same `coding_loop_id` to store the merged CriticFeedback.

### Consolidator Role

The review-consolidator is a meta-agent that reads other reviewers' outputs. It knows:

- Which section keys to look for (via `list_review_sections`)
- How to parse scores from each section's markdown headers
- How to calculate the weighted overall score (core + specialist adjustments)
- How to merge all issues and recommendations with source attribution

This is a pragmatic exception to strict agent isolation — the consolidator needs to know the
output format of other reviewers to merge them. However, it has no knowledge of reviewer
behavior, workflow orchestration, or quality gates.

### Reviewer Agent Template Pattern

```markdown
---
name: respec-{reviewer-name}
description: {single responsibility description}
model: sonnet
tools: {MCP tools for retrieval + storage, builtin tools for code inspection}
---

You are a {specialty} specialist focused on {evaluation area}.

## Invocation Contract

### Scalar Inputs
- coding_loop_id: Loop identifier for feedback retrieval and review section storage
- task_loop_id: Loop identifier for Task retrieval (different from coding_loop_id)
- plan_name: Project name
- phase_name: Phase name for context

### Grouped Markdown Inputs
- workflow_guidance_markdown

### Retrieved Context (Not Invocation Inputs)
- Task document
- Phase document
- Previous feedback

TASKS:
1. Retrieve Task (via task_loop_id)
2. Retrieve Phase (via plan_name/phase_name)
3. Retrieve previous feedback (via coding_loop_id) — progress tracking
4. Inspect codebase (Read/Glob/Grep)
5. Assess against criteria
6. Store review section: store_review_section(key="{plan}/{phase}/review-{slug}")

OUTPUTS: Review section in structured markdown with scored subsections
```

### Adding a New Reviewer

1. Create agent template in `src/platform/templates/agents/{name}_reviewer.py`
2. Add tools model class to `src/platform/models.py` (pattern from existing reviewers)
3. Add factory function to `src/platform/template_helpers.py`
4. Register in `src/platform/templates/agents/__init__.py`
5. Register in `src/platform/template_generator.py` (agent name list + generator function)
6. Add enum value to `CriticAgent` in `src/models/enums.py`
7. Update `review_consolidator.py` to include the new section in merge format
8. Update `code_command.py` to add the reviewer to `ACTIVE_REVIEWERS`
9. Update test counts in `test_template_generator.py` and `test_feedback_enums.py`
10. Regenerate templates

## Related Documentation

- [Architecture Guide](ARCHITECTURE.md) - System architecture overview
- [Architecture Analysis](ARCHITECTURE_ANALYSIS.md) - Detailed system analysis  
- [Command Development Lessons](COMMAND_DEVELOPMENT_LESSONS.md) - Template and orchestration patterns
- [MCP Loop Tools Implementation](MCP_LOOP_TOOLS_IMPLEMENTATION.md) - State management and decision engine
