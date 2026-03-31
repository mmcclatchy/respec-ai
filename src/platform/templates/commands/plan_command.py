from textwrap import indent

from src.models.plan import Plan
from src.platform.models import PlanCommandTools


plan_template = Plan(
    plan_name='[Project Name from conversation]',
    executive_summary=(
        '### Vision\n[High-level project vision from conversation]\n\n'
        '### Mission\n[Project mission statement from conversation]\n\n'
        '### Timeline\n[Phased approach from timeline constraints]\n\n'
        '### Budget\n[Budget considerations from resource constraints]'
    ),
    business_objectives=(
        '### Primary Objectives\n[Specific, measurable goals extracted from conversation]\n\n'
        '### Success Metrics\n[Quantitative metrics and qualitative goals]\n\n'
        '### Key Performance Indicators\n[Key metrics to track project success]'
    ),
    plan_scope=(
        '### Included Features\n[Core features and capabilities from requirements]\n\n'
        '### Anti-Requirements\n[From conversation — things system must NOT do]\n\n'
        '### Assumptions\n[Key assumptions underlying the project plan]\n\n'
        '### Constraints\n[Integration and technology limitations]'
    ),
    stakeholders=(
        '### Plan Sponsor\n[Project sponsor from stakeholder discussion]\n\n'
        '### Key Stakeholders\n[Primary stakeholders from conversation context]\n\n'
        '### End Users\n[Target users and user groups from requirements]'
    ),
    architecture_direction=(
        '### Architecture Overview\n[Component structure, integration points, deployment model]\n\n'
        '### Data Flow\n[Data movement and transformation from architecture discussion]'
    ),
    technology_decisions=(
        '### Chosen Technologies\n[Chosen technologies with justification]\n\n'
        '### Rejected Technologies\n[Rejected technologies with specific reasons]'
    ),
    plan_structure=(
        '### Work Breakdown\n[High-level work breakdown from project structure]\n\n'
        '### Phases Overview\n[Project phases from timeline and scope conversation]\n\n'
        '### Dependencies\n[Dependencies identified from requirements and constraints]'
    ),
    resource_requirements=(
        '### Team Structure\n[Team composition from resource requirements]\n\n'
        '### Technology Requirements\n[Technology stack — include Claude Plan reference if applicable]\n\n'
        '### Infrastructure Needs\n[Infrastructure requirements from resource discussion]'
    ),
    risk_management=(
        '### Identified Risks\n[Technical risks with severity and mitigation]\n\n'
        '### Mitigation Strategies\n[Risk mitigation approaches]\n\n'
        '### Contingency Plans\n[Backup plans for major risks identified]'
    ),
    quality_assurance=(
        '### Quality Bar\n[Quantified quality thresholds and performance targets]\n\n'
        '### Testing Strategy\n[Testing approach from quality requirements]\n\n'
        '### Acceptance Criteria\n[Acceptance criteria from success metrics discussion]'
    ),
).build_markdown()


def generate_plan_command_template(tools: PlanCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [starting-prompt]
description: Orchestrate strategic planning workflow
---

# Strategic Planning Orchestration

## Step 0: Load Existing Plan from Platform

Load existing project plan from platform (if exists):

```text
{tools.sync_plan_instructions}
```

## Context Variables

All respec-ai MCP tools require project context:
- **PLAN_NAME**: From config - used as identifier for all MCP storage operations

Example usage: `{tools.initialize_analyst_loop}`

## State Management

### Track only essential orchestration state

- **PLAN_NAME**: String from user command arguments - used as identifier for MCP plan storage and file/platform naming
- **CONVERSATION_CONTEXT**: Markdown document returned from /respec-plan-conversation - conversation results from Step 2
- **CURRENT_PLAN**: String markdown - the strategic plan document created in Step 3
- **CRITIC_FEEDBACK**: String markdown - feedback returned from plan-critic agent in Step 4
- **QUALITY_SCORE**: Integer parsed from CRITIC_FEEDBACK - for user decision support
- **USER_DECISION**: String from user choice - values: "continue_conversation", "refine_plan", "accept_plan"
- **PLAN_LOOP_ID**: String returned from MCP `{tools.initialize_plan_loop}` - used for feedback storage during human-driven plan refinement (Steps 3-5)
- **ANALYST_LOOP_ID**: String returned from MCP `{tools.initialize_analyst_loop}` - required for MCP loop management during analyst validation (Steps 6-9)
- **ANALYST_SCORE**: Integer from analyst-critic feedback retrieval - needed for MCP loop decisions

### Data Storage Pattern

Human-driven phase (Steps 1-5):
- Initializes plan quality loop with PLAN_LOOP_ID for feedback tracking
- Uses variables for orchestration state (CONVERSATION_CONTEXT, CURRENT_PLAN, CRITIC_FEEDBACK)
- Stores plan in MCP using PLAN_NAME: `{tools.store_plan}`
- Writes plan to external file/platform using platform-specific tools
- Plan-critic returns feedback to Main Agent (not stored in MCP during human phase)
- User feedback stored via `{tools.store_user_feedback}` when user provides guidance

Automated analyst phase (Steps 6-9):
- Initializes MCP refinement loop with ANALYST_LOOP_ID
- Stores plan copy in analyst loop: `{tools.store_plan_in_loop}`
- Analyst agents use ANALYST_LOOP_ID for all MCP operations
- MCP Server manages loop state and decisions

{tools.mcp_tools_reference}

## Step 1: Initialize Conversation Context

### Set up the conversational planning workflow

### Set initial context
- Extract PLAN_NAME from first argument in `$ARGUMENTS`
- Use remaining arguments as initial conversation context
- If no conversation context provided, start with: "I need help creating a strategic plan for my project"
- Initialize variables for state management throughout the human-driven process

## Step 1.5: Detect Claude Plan File

Check for pre-resolved architecture decisions in a Claude Plan file:

```text
CLAUDE_PLAN_FILE = None
CLAUDE_PLAN_CONTEXT = None

Check remaining arguments (after PLAN_NAME) for a file path argument
(contains {tools.plans_dir}/ or ends in .md with a path separator):
  IF found: CLAUDE_PLAN_FILE = extracted path

IF CLAUDE_PLAN_FILE is None:
  Bash: find {tools.plans_dir} -name "*.md" -mtime -7 -type f 2>/dev/null | head -5
  IF results found:
    Use AskUserQuestion:
      Question: "I found recently modified Claude Plan file(s). Use one as a starting point?"
      Header: "Select Claude Plan"
      multiSelect: false
      Options: [each file path found, plus "No, proceed without a Claude Plan"]
    IF user selects a file: CLAUDE_PLAN_FILE = selected path
    IF user declines: CLAUDE_PLAN_FILE = None

IF CLAUDE_PLAN_FILE is not None:
  CALL Read(CLAUDE_PLAN_FILE)
  CLAUDE_PLAN_CONTEXT = [content read from file]
  Display: "✓ Using Claude Plan: {{CLAUDE_PLAN_FILE}}"
ELSE:
  Display: "ℹ️ No Claude Plan file detected — proceeding with standard workflow"
```

## Step 2: Conversational Requirements Gathering

### Use the /respec-plan-conversation command to conduct conversational discovery

Invoke the plan-conversation command with initial context. Pass the remaining arguments (after PLAN_NAME) as the initial conversation context:

```text
IF CLAUDE_PLAN_CONTEXT is not None:
  CONVERSATION_INITIAL_CONTEXT = (
    "Context from Claude Plan ({{CLAUDE_PLAN_FILE}}): key technology decisions, "
    "architecture constraints, and rejected alternatives are pre-resolved. "
    "These decisions are already settled — focus the conversation on project "
    "goals, requirements, and areas not covered by the Claude Plan. "
    + [remaining arguments after PLAN_NAME, if any]
  )
ELSE:
  CONVERSATION_INITIAL_CONTEXT = [remaining arguments after PLAN_NAME, or
    "I need help creating a strategic plan for my project"]
```

{tools.conversation_invocation}

{tools.conversation_workflow_name.capitalize()} will conduct the multi-stage conversation and return structured conversation context in the CONVERSATION_CONTEXT variable.

Expected structured format from plan-conversation (markdown document):
```markdown
## Vision and Objectives
### Problem Statement
[Description of problem or opportunity]

### Desired Outcome
[What success looks like]

### Success Metrics
[How success will be measured]

## Business Context
### Business Drivers
[Key business motivations]

### Stakeholder Needs
[Primary stakeholders and needs]

### Organizational Constraints
[Organizational limitations]

## Requirements
### Functional Requirements
- [Specific capabilities]

### User Experience Requirements
- [User-facing requirements]

### Integration Requirements
- [System integrations]

### Performance Requirements
- [Performance targets]

### Security Requirements
- [Security needs]

### Technical Constraints
- [Technical limitations]

## Constraints
### Timeline Constraints
- [Time-related constraints]

### Resource Constraints
- [Resource limitations]

### Business Constraints
- [Business policies]

## Priorities
### Must-Have Features
- [Critical requirements]

### Nice-to-Have Features
- [Desirable features]

## Technology Context

### Preferred Stack
[Deployment target and general technology preferences]

### Technology Decisions
- [Technology chosen — justification]

### Rejected Technologies
- [Technology rejected — specific reason]

## Architecture Direction
[High-level component structure, integration points, deployment model, data flow]

## Scope Boundaries

### Anti-Requirements
- [Thing system must NOT do]

### Performance Targets
- [Quantified performance/scale target]

## Risk Assessment
- [Technical risk with severity/likelihood/mitigation]

## Quality Bar
[Test coverage minimum, security requirements, accessibility standards]

## Conversation Summary
- **Total Stages Completed**: 6
- **Key Insights**: [Main discoveries]
- **Areas of Emphasis**: [Topics focused on]
- **User Engagement Level**: [High/Medium/Low]
```

## Step 3: Create Strategic Plan Document

### Initialize plan quality loop (once only)

If PLAN_LOOP_ID does not yet exist, initialize the plan quality loop:
- Call `{tools.initialize_plan_loop}`
- Store the returned loop ID as `PLAN_LOOP_ID`
- This enables user feedback storage during plan refinement

### Transform conversation context into a strategic plan document

Use the CONVERSATION_CONTEXT variable returned from Step 2 to create the strategic plan:

### Create strategic plan using template
   ```markdown
{indent(plan_template, '   ')}
   ```

### DOCUMENT STRUCTURE CONSTRAINTS (MANDATORY)

The Plan model enforces H2 headers as its schema. Violating these constraints causes silent data loss.

**DO**:
- Use ONLY these H2 sections: Executive Summary, Business Objectives, Plan Scope, Stakeholders, Architecture Direction, Technology Decisions, Plan Structure, Resource Requirements, Risk Management, Quality Assurance
- Structure content freely within each H2 using H3-H6 sub-headers, bullet lists, code blocks, tables
- Keep all content within the defined H2 sections

**DO NOT**:
- Add H2 headers not in the list above (they will be lost on subsequent retrievals)
- Remove or rename any of the defined H2 headers
- Add a Metadata section (the system manages this automatically)

The H3 headers shown in the template (### Vision, ### Mission, etc.) are suggested structure, not enforced. You may add, rename, or reorganize H3+ headers within any H2 section.

Strategic plan creation process:
1. **Use conversation context** from CONVERSATION_CONTEXT variable
2. **Structure into strategic plan format** using the template above
3. **Incorporate previous feedback** if CRITIC_FEEDBACK variable exists from prior iterations
4. **If CLAUDE_PLAN_FILE is not None**: You MUST append this exact line to the resource_requirements section:
   `Claude Plan: {{CLAUDE_PLAN_FILE}}` — phase-architect reads this as hard constraints.
   Do NOT inline the decisions and omit the file path. The path is how downstream agents access the full implementation details.
5. **Store in variable** as CURRENT_PLAN for next steps
6. **Store in MCP** using: `{tools.store_plan}`

## Step 3.2: Write Plan to External File/Platform

### Make the plan visible to the user BEFORE requesting acceptance

Write the strategic plan to the user's platform using the platform-specific tool:
```text
{tools.create_project_tool_interpolated}
```

This creates:
- {tools.plan_resource_example}

The user can now review the plan file before making their decision.

## Step 4: Quality Assessment

Invoke the plan-critic agent with project name for plan retrieval:

{tools.invoke_plan_critic}

### Plan-critic workflow
1. **Agent retrieves strategic plan** from MCP using `{tools.get_plan}`
2. **Agent evaluates plan** against FSDD framework
3. **Agent returns feedback markdown** to Main Agent (human-driven workflow)

### Extract quality score from returned feedback
Store the returned feedback markdown as CRITIC_FEEDBACK variable.

Parse the QUALITY_SCORE from the markdown:
```text
Extract "Overall Score: [number]" from CRITIC_FEEDBACK markdown
Store as QUALITY_SCORE variable
```

## Step 5: Present Quality Assessment and User Decision

### Present the quality assessment to the user

Display the quality feedback from CRITIC_FEEDBACK variable:

```text
Display QUALITY_SCORE and CRITIC_FEEDBACK to user
```

Present options to user:

   ```markdown
   ## Strategic Plan Quality Assessment

   #### Plan Location
   [Display path to the plan file created in Step 3.2]

   #### Plan Overview
   - Quality Score: [QUALITY_SCORE from CRITIC_FEEDBACK]%

   #### Quality Summary
   [Display CRITIC_FEEDBACK markdown - the full feedback from plan-critic]

   #### Your Options

   1. **Continue conversation** - Add more details via {tools.conversation_workflow_name}
      - Best if: Missing requirements, unclear scope, or need more context
      - Action: Return to conversational discovery for specific areas

   2. **Refine plan** - Generate improved version addressing feedback
      - Best if: Content exists but needs better organization or clarity
      - Action: Create new strategic plan version with targeted improvements

   3. **Accept plan** - Proceed with current plan to objective extraction
      - Best if: Plan meets your needs and you're ready to move forward
      - Action: Continue to automated objective validation phase

   #### Please choose your preferred option (1, 2, or 3)
   ```

### Wait for user response and process decision

```text
IF user provides feedback along with their choice:
  Store user feedback: {tools.store_user_feedback}
  This preserves user guidance for subsequent plan/critic iterations

IF user chooses "1" (Continue conversation):
  Set USER_DECISION = "continue_conversation"
  CONVERSATION_CONTEXT and CURRENT_PLAN still in context/variables
  Return to Step 2 to add more details via {tools.conversation_workflow_name}

ELIF user chooses "2" (Refine plan):
  Set USER_DECISION = "refine_plan"
  CRITIC_FEEDBACK now available for refinement guidance
  Return to Step 3 to generate improved strategic plan incorporating feedback
  Step 3.2 will update the external plan file

ELIF user chooses "3" (Accept plan):
  Set USER_DECISION = "accept_plan"
  Strategic plan already stored in MCP from Step 3
  Plan file already written in Step 3.2
  Proceed to Step 6 for automated objective extraction
```

## Error Recovery and Resilience

### Agent Invocation Failures

**strategic plan creation failures:**
1. **Empty or Invalid Context**: If CONVERSATION_CONTEXT is empty or malformed:
   - Retry {tools.conversation_workflow_name} with same initial context
   - If second attempt fails, continue with placeholder: "Plan creation failed - proceeding with basic template"
   - Update CURRENT_PLAN with failure notification for critic evaluation

2. **Context Overflow**: If CONVERSATION_CONTEXT exceeds processing limits:
   - Trigger context summarization: Extract key points from CONVERSATION_CONTEXT
   - Create strategic plan with summarized context (max 2000 characters)
   - If still fails, proceed with minimal template-based planning

3. **Template Processing Errors**: If strategic plan template cannot be populated:
   - Continue with basic markdown structure
   - Document template failure in CURRENT_PLAN output
   - Notify user of reduced functionality

**plan-critic failures:**
1. **Score Extraction Failure**: If QUALITY_SCORE cannot be parsed:
   - Use fallback score for MCP decision processing
   - Set CRITIC_FEEDBACK = "Critic assessment failed - manual review required"
   - Continue refinement loop with manual oversight

2. **Empty Feedback**: If CRITIC_FEEDBACK is empty or unparsable:
   - Set CRITIC_FEEDBACK = "General improvement needed - refine based on FSDD framework"
   - Continue with generic refinement guidance

**plan-analyst failures:**
1. **Objective Extraction Failure**: If plan-analyst returns invalid structure:
   - Retry once with explicit format requirements
   - If still fails, provide manual objective extraction template
   - Continue with basic objective structure

### MCP Tool Failures

**initialize_analyst_loop failures (analyst phase only):**
1. **Loop Creation Error**: If ANALYST_LOOP_ID generation fails:
   - Generate local tracking ID (timestamp-based) for analyst phase
   - Continue without MCP loop management for analyst validation
   - Use fallback decision logic without MCP guidance for analyst refinement

2. **Server Unavailable**: If MCP server is unreachable:
   - Fall back to local analyst loop management
   - Display warning: "MCP analyst loop management unavailable - using local fallback"

**decide_loop_action failures:**
1. **Decision Service Error**: If decision cannot be retrieved:
   - Apply basic fallback decision logic based on previous iteration patterns
   - Continue with fallback decision
   - Log decision reasoning for user

### Context Management Edge Cases

#### Context Window Exhaustion
1. **Warning Threshold (80% capacity)**:
   - Trigger progressive summarization of CONVERSATION_CONTEXT
   - Preserve most recent 20% and highest-priority 30% of content
   - Continue with condensed context

2. **Critical Threshold (95% capacity)**:
   - Emergency context compression: Keep only current iteration data
   - Store full context in CURRENT_PLAN for persistence
   - Notify user of context limitation

3. **Context Loss Recovery**:
   - If context is lost during processing, attempt recovery from CURRENT_PLAN
   - Use plan-analyst to reconstruct key requirements
   - Continue with reconstructed minimal context

#### Variable State Corruption
1. **Missing Variables**: If any tracked variable becomes undefined:
   - Reinitialize with safe defaults
   - Attempt recovery from previous agent outputs
   - Continue with recovered or default values

2. **Invalid Variable Types**: If variables contain unexpected data types:
   - Clean and convert to expected format
   - Log data cleaning actions
   - Continue with sanitized variables

## Step 6: Initialize Analyst Validation Loop

### Initialize the MCP refinement loop for analyst validation

{tools.initialize_refinement_loop_inline_doc}

Use the MCP tool `{tools.initialize_analyst_loop}`:
- Call `{tools.initialize_analyst_loop}`
- Store the returned loop ID as `ANALYST_LOOP_ID` for tracking throughout the analyst validation process
- Retrieve the strategic plan from MCP using `{tools.get_plan}`
- Store it in the analyst loop using `{tools.store_plan_in_loop}`

## Step 7: Extract Objectives

After plan acceptance, invoke the plan-analyst agent with analyst loop ID:

{tools.invoke_plan_analyst}

### Plan-analyst workflow
1. **Agent retrieves strategic plan** from MCP using get_plan_markdown(ANALYST_LOOP_ID)
2. **Agent checks for previous analysis** using get_previous_analysis(ANALYST_LOOP_ID)
3. **Agent extracts structured objectives** from strategic plan
4. **Agent stores analysis** using store_current_analysis(ANALYST_LOOP_ID, analysis)

## Step 8: Analyst Quality Assessment

Invoke the analyst-critic agent with loop ID:

{tools.invoke_analyst_critic}

### Analyst-critic workflow
1. **Agent retrieves business objectives analysis** from MCP using get_previous_analysis(ANALYST_LOOP_ID)
2. **Agent retrieves original strategic plan** from MCP using get_plan_markdown(ANALYST_LOOP_ID)
3. **Agent validates extraction quality** against validation framework
4. **Agent stores analysis feedback** using store_current_analysis(ANALYST_LOOP_ID, analysis)

### Extract analyst score for MCP decision
```text
Retrieve feedback using: {tools.get_previous_analysis}
Extract ANALYST_SCORE from feedback overall_score field
```

## Step 9: Analyst Validation Loop

### Call the MCP Server for analyst validation decision

```text
ANALYST_LOOP_RESPONSE = {tools.decide_loop_action}
ANALYST_LOOP_STATUS = ANALYST_LOOP_RESPONSE.status
ANALYST_SCORE = ANALYST_LOOP_RESPONSE.current_score
ANALYST_ITERATION = ANALYST_LOOP_RESPONSE.iteration

Decision options: "completed", "refine", "user_input"
```

**Follow ANALYST_LOOP_STATUS exactly. Do not override based on score assessment.**

```text
IF ANALYST_LOOP_STATUS == "refine":
  Display: "⟳ Iteration {{ANALYST_ITERATION}} · Score: {{ANALYST_SCORE}}/100 — refining analyst validation"
  Return to Step 7 (plan-analyst will retrieve feedback from MCP itself)

ELIF ANALYST_LOOP_STATUS == "user_input":
  Display: "⚠ Iteration {{ANALYST_ITERATION}} · Score: {{ANALYST_SCORE}}/100 — user input required"
  LATEST_FEEDBACK = {tools.get_previous_analysis}
  Present LATEST_FEEDBACK to user with current score and iteration
  Wait for user response
  Store user feedback: {tools.store_user_feedback}
  Return to Step 7

ELIF ANALYST_LOOP_STATUS == "completed":
  Display: "✅ Score: {{ANALYST_SCORE}}/100 — analyst validation complete"
  Create external project using {tools.create_project_tool_interpolated}
  Proceed to Step 10.
```

## Step 10: Automatic Roadmap Generation

After analyst validation completes, automatically generate the roadmap:

```text
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Display: "✅  PLAN COMPLETE — generating roadmap"
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

Invoke the roadmap command to decompose the plan into phases:

```bash
/respec-roadmap {{PLAN_NAME}}
```

The `/respec-roadmap` command will:
1. Retrieve the strategic plan from MCP
2. Initialize a roadmap quality loop
3. Run roadmap agent → roadmap-critic refinement cycle
4. Create sparse phase files for each phase in the roadmap

**If /respec-roadmap fails**: The plan is already stored and valid. Display:
```text
"⚠ Roadmap generation failed. Plan is saved. Run /respec-roadmap {{PLAN_NAME}} manually."
```

**After /respec-roadmap completes**: Present final summary:

```text
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Display: "✅  PLAN AND ROADMAP COMPLETE"
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

**Summary**:
- Plan quality score: [score]
- Analyst validation score: [score]
- Phases generated: [list phase names from roadmap]

**Next Steps**:
Run `/respec-phase {{PLAN_NAME}} [phase-name]` to expand a phase with architecture detail.
```
"""
