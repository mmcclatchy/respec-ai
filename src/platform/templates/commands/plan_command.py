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
        '### Technology Requirements\n[Technology stack — include plan reference if applicable]\n\n'
        '### Infrastructure Needs\n[Infrastructure requirements from resource discussion]'
    ),
    risk_management=(
        '### Identified Risks\n[Technical risks with severity and mitigation]\n\n'
        '### Mitigation Strategies\n[Risk mitigation approaches]\n\n'
        '### Contingency Plans\n[Backup plans for major risks identified]'
    ),
    quality_assurance=(
        '### Quality Bar\n[Quantified quality thresholds and performance targets]\n\n'
        '### Delivery Intent Policy\n'
        '- Default Mode: [MVP|hardening]\n'
        '- Tie-Break Policy: [How to resolve MVP-vs-hardening conflicts]\n'
        '- Deferred Risk Rule: [How accepted risks are tracked/suppressed during the chosen mode]\n\n'
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
- **CONVERSATION_CONTEXT**: Markdown document returned from the conversation workflow - conversation results from Step 2
- **CURRENT_PLAN**: String markdown - the strategic plan document created in Step 3
- **CRITIC_FEEDBACK**: String markdown - feedback returned from plan-critic agent in Step 4
- **QUALITY_SCORE**: Integer parsed from CRITIC_FEEDBACK - for user decision support
- **BLOCKERS_LIST**: List of structural/procedural blockers parsed from CRITIC_FEEDBACK `### Blockers`
- **BLOCKERS_ACTIVE**: Boolean (`len(BLOCKERS_LIST) > 0`) controlling acceptance gating in human phase
- **LAST_BLOCKER_SIGNATURE**: String fingerprint of blockers from previous iteration (for stagnation tracking)
- **PLAN_BLOCKER_STAGNATION_COUNT**: Integer count of consecutive iterations with unchanged active blockers
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
  - `BLOCKERS_LIST = []`
  - `BLOCKERS_ACTIVE = false`
  - `LAST_BLOCKER_SIGNATURE = ""`
  - `PLAN_BLOCKER_STAGNATION_COUNT = 0`

## Step 1.5: Detect and Capture TUI Plan Reference (Fail-Closed)

Check for pre-resolved architecture decisions from a TUI plan source.
Accepted inputs are ONLY:
1) explicit file path, or
2) full inline markdown plan content.

```text
PLAN_REFERENCE_FILE = None
PLAN_REFERENCE_CONTEXT = None
PLAN_REFERENCE_SOURCE = None

REMAINING_INPUT = [all arguments after PLAN_NAME]

STEP A: Detect explicit file path in REMAINING_INPUT
  IF argument contains {tools.plans_dir}/ OR argument ends in .md with a path separator:
    PLAN_REFERENCE_FILE = extracted path
    PLAN_REFERENCE_SOURCE = "file-path"

STEP B: Detect full inline plan content in REMAINING_INPUT
  IF PLAN_REFERENCE_FILE is None:
    IF REMAINING_INPUT contains "<proposed_plan>" and "</proposed_plan>":
      PLAN_REFERENCE_CONTEXT = [full content inside block]
      PLAN_REFERENCE_SOURCE = "inline-proposed-plan"
    ELIF REMAINING_INPUT contains full markdown plan body
         (title + multiple markdown headings, not a short summary):
      PLAN_REFERENCE_CONTEXT = [full inline markdown plan]
      PLAN_REFERENCE_SOURCE = "inline-markdown"

STEP C: Detect reference-intent language (without usable source)
  PLAN_REFERENCE_INTENT = REMAINING_INPUT contains phrases like:
    "use my plan", "use the TUI plan", "based on previous plan", "use existing plan"

FAIL-CLOSED RULE:
  IF PLAN_REFERENCE_INTENT is true AND PLAN_REFERENCE_SOURCE is None:
    ERROR: "Plan reference mentioned but no readable source provided."
    GUIDANCE:
      - "Provide a path to a markdown plan file, OR"
      - "Paste the FULL plan markdown (recommended: <proposed_plan>...</proposed_plan>)."
    STOP workflow (do NOT continue with inferred summary)

IF PLAN_REFERENCE_FILE is not None:
  CALL Read(PLAN_REFERENCE_FILE)
  PLAN_REFERENCE_CONTEXT = [content read from file]
  Display: "✓ Loaded plan reference from file: {{PLAN_REFERENCE_FILE}}"

IF PLAN_REFERENCE_CONTEXT is None:
  Display: "ℹ️ No plan reference source provided — proceeding with standard workflow"
```

## Step 1.7: Canonical Reference Copy to Project

Always persist accepted plan reference content into the project so downstream
agents can reliably Read() the same source.

```text
IF PLAN_REFERENCE_CONTEXT is not None:
  REFERENCE_FILENAME = [derive from source:
    - file path basename when source is file-path
    - "tui-plan-reference.md" when source is inline]

  REFERENCE_FILENAME = [normalize to lowercase-kebab-case filename ending in .md]
  REFERENCE_PATH = .respec-ai/plans/{{PLAN_NAME}}/references/{{REFERENCE_FILENAME}}

  IF REFERENCE_PATH already exists:
    REFERENCE_PATH = [append -2, -3, ... before .md until unique]

  CALL Write(REFERENCE_PATH, PLAN_REFERENCE_CONTEXT)
  Display: "✓ Stored canonical plan reference: {{REFERENCE_PATH}}"

  PLAN_REFERENCE_FILE = REFERENCE_PATH
```

## Step 2: Conversational Requirements Gathering

### Use the conversation workflow to conduct conversational discovery

Invoke the conversation workflow with initial context. Pass the remaining arguments (after PLAN_NAME) as the initial conversation context:

```text
IF PLAN_REFERENCE_CONTEXT is not None:
  CONVERSATION_INITIAL_CONTEXT = (
    "Context from plan reference ({{PLAN_REFERENCE_FILE}}): key technology decisions, "
    "architecture constraints, and rejected alternatives are pre-resolved. "
    "These decisions are already settled — focus the conversation on project "
    "goals, requirements, and areas not covered by the plan reference. "
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
Delivery Intent Default: [MVP|hardening]
Intent Tie-Break Policy: [How to resolve MVP vs hardening conflicts]

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

═══════════════════════════════════════════════
MANDATORY DOCUMENT STRUCTURE GATE
═══════════════════════════════════════════════
Your strategic plan MUST contain EXACTLY these 10 H2 sections:
Executive Summary, Business Objectives, Plan Scope, Stakeholders,
Architecture Direction, Technology Decisions, Plan Structure,
Resource Requirements, Risk Management, Quality Assurance.

Any content under a non-listed H2 header is silently dropped on
retrieval. Adding "## Implementation Details" or "## Timeline"
causes that content to vanish permanently.

VIOLATION: Adding any H2 header not in the list above.
           Content under unauthorized H2 headers is permanently lost.
═══════════════════════════════════════════════

Strategic plan creation process:
1. **Use conversation context** from CONVERSATION_CONTEXT variable
2. **Structure into strategic plan format** using the template above
3. **Resolve delivery intent defaults from conversation context**:
   - Parse `Delivery Intent Default` and `Intent Tie-Break Policy` from conversation Quality Bar
   - If missing/ambiguous, default to:
     - Default Mode: MVP
     - Tie-Break Policy: "When in doubt, prioritize core functional/spec delivery and defer non-P0 hardening risks."
4. **Persist Delivery Intent Policy in Plan `## Quality Assurance`** using a structured `### Delivery Intent Policy` block
5. **Incorporate previous feedback** if CRITIC_FEEDBACK variable exists from prior iterations
6. **If PLAN_REFERENCE_FILE is not None**: You MUST append this exact line to the resource_requirements section:
   `Plan Reference: {{PLAN_REFERENCE_FILE}}` — phase-architect reads this as hard constraints.
   Do NOT inline the decisions and omit the file path. The path is how downstream agents access the full implementation details.
7. **MUST store in variable** as CURRENT_PLAN — required for Steps 4 and 5
8. **MUST store in MCP** using: `{tools.store_plan}` — verify storage succeeds before proceeding
   IF MCP storage fails: retry once. IF second attempt fails: display error and STOP.

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
2. **If refinement iteration**: agent reads `previous_feedback_markdown` grouped input and compares resolved vs unresolved issues
3. **Agent evaluates plan** against FSDD framework
4. **Agent returns feedback markdown** to Main Agent (human-driven workflow)

### Extract quality score from returned feedback
Before invocation:
```text
IF CRITIC_FEEDBACK exists from a previous iteration:
  PRIOR_CRITIC_FEEDBACK = CRITIC_FEEDBACK
ELSE:
  PRIOR_CRITIC_FEEDBACK = ""
```

Store the returned feedback markdown as CRITIC_FEEDBACK variable.

Parse the QUALITY_SCORE from the markdown:
```text
Extract "Overall Score: [number]" from CRITIC_FEEDBACK markdown
Store as QUALITY_SCORE variable
```

Parse structural blockers separately from score:
```text
BLOCKERS_LIST = []
Extract each bullet from "### Blockers" in CRITIC_FEEDBACK
Ignore "None identified" placeholder rows
BLOCKERS_ACTIVE = len(BLOCKERS_LIST) > 0

CURRENT_BLOCKER_SIGNATURE = "|".join(sorted(lowercase(trim(BLOCKERS_LIST))))
IF BLOCKERS_ACTIVE:
  IF CURRENT_BLOCKER_SIGNATURE == LAST_BLOCKER_SIGNATURE:
    PLAN_BLOCKER_STAGNATION_COUNT += 1
  ELSE:
    PLAN_BLOCKER_STAGNATION_COUNT = 1
  LAST_BLOCKER_SIGNATURE = CURRENT_BLOCKER_SIGNATURE
ELSE:
  PLAN_BLOCKER_STAGNATION_COUNT = 0
  LAST_BLOCKER_SIGNATURE = ""

BLOCKER_STAGNATION = (PLAN_BLOCKER_STAGNATION_COUNT >= 3)
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
   - Structural Blockers Active: [BLOCKERS_ACTIVE]

   #### Quality Summary
   [Display CRITIC_FEEDBACK markdown - the full feedback from plan-critic]
   ```

Option gating rules:
```text
IF BLOCKERS_ACTIVE and not BLOCKER_STAGNATION:
  Display:
    "Structural blockers are active. Auto-refining plan until blockers clear or stagnation is detected."
  Set USER_DECISION = "refine_plan"
  IMMEDIATELY return to Step 3 using CRITIC_FEEDBACK as refinement guidance
  Do NOT prompt user in this state
ELSE:
  Present options:
    1. Continue conversation
    2. Refine plan
    3. Accept plan
  Prompt: "Please choose your preferred option (1, 2, or 3)"
```

### Wait for user response and process decision

```text
STEP 1: Check for user feedback
IF user response contains text beyond just a number (1, 2, or 3):
  Store user feedback: {tools.store_user_feedback}
  This preserves user guidance for subsequent plan/critic iterations

STEP 2: Process user choice (EXHAUSTIVE — every case handled)

IF user chooses "1" (Continue conversation):
  Set USER_DECISION = "continue_conversation"
  CONVERSATION_CONTEXT and CURRENT_PLAN still in context/variables
  IMMEDIATELY return to Step 2 to add more details via {tools.conversation_workflow_name}

ELIF user chooses "2" (Refine plan):
  Set USER_DECISION = "refine_plan"
  CRITIC_FEEDBACK now available for refinement guidance
  IMMEDIATELY return to Step 3 to generate improved strategic plan incorporating feedback
  Step 3.2 will update the external plan file

ELIF user chooses "3" (Accept plan):
  Set USER_DECISION = "accept_plan"
  Strategic plan already stored in MCP from Step 3
  Plan file already written in Step 3.2
  IMMEDIATELY proceed to Step 6 for automated objective extraction

ELSE (user response does not match 1, 2, or 3):
  Display: "Please choose option 1, 2, or 3."
  Wait for user response again.
  Return to STEP 1 of this decision block.
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
   - Set QUALITY_SCORE = 50 (fallback score indicating critic assessment unavailable)
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
3. **Agent retrieves latest analyst-critic feedback** using get_feedback(ANALYST_LOOP_ID, count=1) on refinement iterations
4. **Agent extracts structured objectives** from strategic plan
5. **Agent stores analysis** using store_current_analysis(ANALYST_LOOP_ID, analysis)

## Step 8: Analyst Quality Assessment

Invoke the analyst-critic agent with loop ID:

{tools.invoke_analyst_critic}

### Analyst-critic workflow
1. **Agent retrieves business objectives analysis** from MCP using get_previous_analysis(ANALYST_LOOP_ID)
2. **Agent retrieves original strategic plan** from MCP using get_plan_markdown(ANALYST_LOOP_ID)
3. **Agent retrieves prior analyst-critic feedback** using get_feedback(ANALYST_LOOP_ID, count=2) when refinement history exists
4. **Agent validates extraction quality** against validation framework
5. **Agent stores CriticFeedback** using store_critic_feedback(ANALYST_LOOP_ID, feedback_markdown)

### Extract analyst score for MCP decision
```text
Retrieve feedback using: {tools.get_feedback}
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

═══════════════════════════════════════════════
MANDATORY DECISION PROTOCOL
═══════════════════════════════════════════════
The MCP decision is FINAL. Execute the matching branch IMMEDIATELY.

"refine"     → Execute refinement. Do NOT ask, confirm, or present options to the user.
"user_input" → ONLY status that involves the user. Present feedback and wait for response.
"completed"  → Proceed to next step. Do NOT ask for confirmation.

VIOLATION: Asking the user "Should I continue refining?" when status is "refine"
           is a workflow violation. The decision has already been made by the MCP server.
═══════════════════════════════════════════════

```text
IF ANALYST_LOOP_STATUS == "refine":
  Display: "⟳ Iteration {{ANALYST_ITERATION}} · Score: {{ANALYST_SCORE}}/100 — refining analyst validation"
  Return to Step 7 (plan-analyst will retrieve feedback from MCP itself)

ELIF ANALYST_LOOP_STATUS == "user_input":
  Display: "⚠ Iteration {{ANALYST_ITERATION}} · Score: {{ANALYST_SCORE}}/100 — user input required"
  LATEST_FEEDBACK = {tools.get_feedback}
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

═══════════════════════════════════════════════
MANDATORY ROADMAP HANDOFF PROTOCOL (FAIL-CLOSED)
═══════════════════════════════════════════════
MUST:
- Attempt roadmap generation in the SAME run via:
  {tools.roadmap_command_invocation}
- Record roadmap invocation outcome before any completion response

MUST NOT:
- Return "Plan complete" success without attempting Step 10
- Attempt `respec-roadmap` invocation via Bash/CLI

EXCEPTION:
- Only skip automatic chaining if user explicitly instructed to stop chaining

IMPORTANT:
- Fallback/manual mode changes implementation method only.
- Fallback/manual mode does NOT waive Step 10 obligations.
- Command handoff path MUST use adapter-rendered orchestration invocation, not shell fallback.
═══════════════════════════════════════════════

```text
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Display: "✅  PLAN COMPLETE — generating roadmap"
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ROADMAP_INVOCATION_ATTEMPTED = false
ROADMAP_INVOCATION_STATUS = "failed"
ROADMAP_INVOCATION_METHOD = "orchestration"
ROADMAP_IDENTIFIER = "unavailable"
ROADMAP_ERROR_SUMMARY = ""

Sanity check orchestration path:
ROADMAP_ORCHESTRATION_INVOCATION = "{tools.roadmap_command_invocation}"
IF ROADMAP_ORCHESTRATION_INVOCATION is empty OR missing expected respec-roadmap invocation text:
  ERROR_RESPONSE = {{
    "error_type": "roadmap_handoff_unavailable",
    "error_message": "Roadmap orchestration invocation path unavailable",
    "recovery_action": "Stop before Step 10 execution and preserve plan output",
    "user_guidance": "Run template regeneration and retry Plan workflow. Do NOT use shell fallback for respec-roadmap.",
    "partial_output": "Plan saved successfully; roadmap handoff blocked by fail-closed policy."
  }}
  EXIT: Workflow terminated

Attempt roadmap workflow via orchestration path:
{tools.roadmap_command_invocation}
ROADMAP_INVOCATION_ATTEMPTED = true
ROADMAP_INVOCATION_METHOD = "orchestration"

IF roadmap workflow invocation returns error:
  ROADMAP_INVOCATION_STATUS = "failed"
  ROADMAP_ERROR_SUMMARY = [captured error summary]
ELSE:
  ROADMAP_IDENTIFIER = PLAN_NAME
  Verify roadmap exists in MCP:
  mcp__respec-ai__get_document(
    doc_type="roadmap",
    key=PLAN_NAME,
    loop_id=None
  )

  IF verification succeeds:
    ROADMAP_INVOCATION_STATUS = "succeeded"
  ELSE:
    ROADMAP_INVOCATION_STATUS = "failed"
    ROADMAP_ERROR_SUMMARY = "Roadmap workflow returned but roadmap retrieval verification failed"
```

```text
IF ROADMAP_INVOCATION_ATTEMPTED == false AND user did not explicitly request to stop chaining:
  ERROR: non-compliant run (Step 10 not attempted)
  EXIT with structured error (do NOT report success)

IF ROADMAP_INVOCATION_METHOD == "shell":
  ERROR: non-compliant run (shell invocation is invalid for Step 10)
  RETRY REQUIRED: re-run Step 10 via orchestration invocation path before reporting success/failure
  EXIT with structured error

Completion contract (required in final response):
1. plan_file_path
2. plan_status
3. roadmap_invocation_status ("succeeded" | "failed")
4. roadmap_invocation_method ("orchestration" | "shell"; shell is invalid/non-compliant)
5. roadmap_identifier (MCP key when available, else "unavailable")
6. next_action (required when roadmap_invocation_status == "failed")
```

```text
IF ROADMAP_INVOCATION_STATUS == "succeeded":
  Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  Display: "✅  PLAN AND ROADMAP COMPLETE"
  Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  **Summary**:
  - Plan quality score: [score]
  - Analyst validation score: [score]
  - Roadmap key: [ROADMAP_IDENTIFIER]

  **Next Steps**:
  Use the phase workflow to expand a phase with architecture detail.
  {tools.phase_command_invocation}
ELSE:
  Display:
  "⚠ Roadmap generation failed. Plan is saved. Retry roadmap generation:"
  {tools.roadmap_command_invocation}
  Include error output summary and retry guidance in next_action.
```
"""
