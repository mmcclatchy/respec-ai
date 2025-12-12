from src.models.enums import PhaseStatus
from src.models.phase import Phase
from src.platform.models import PhaseCommandTools


# Create template instance with instructional placeholders
technical_phase_template = Phase(
    phase_name='[phase-name-in-kebab-case]',
    objectives='[Clear, measurable goals with business value]',
    scope="[Boundaries, what's included/excluded, constraints]",
    dependencies='[External requirements with versions and justifications]',
    deliverables='[High-level outputs - no specific file names]',
    architecture='[Component structure, interactions, data flow, design decisions - REQUIRED]',
    technology_stack='[Technologies with versions, justifications, trade-offs - Optional but recommended]',
    functional_requirements='[Features and user workflows]',
    non_functional_requirements='[Performance targets, scalability, availability - quantified where possible]',
    development_plan='[Implementation phases - no time estimates, no file names]',
    testing_strategy='[Coverage approach, test levels, quality gates - strategy not test cases - REQUIRED]',
    research_requirements=(
        '**Existing Documentation**:\n'
        '- Read: [full paths to archive docs]\n\n'
        '**External Research Needed**:\n'
        '- Synthesize: [research prompts with "2025"]'
    ),
    success_criteria='[Measurable outcomes and verification methods]',
    integration_context='[System relationships and interface contracts]',
    additional_sections={
        'Data Models': '[High-level schema, validation rules - ONLY for data-heavy projects]',
        'API Design': '[Interface contracts, behavior - ONLY for web services]',
        'Security Architecture': '[Auth methods, data protection approach - ONLY for security-critical systems]',
        'Performance Requirements': '[Response time targets, scalability constraints - ONLY for performance-critical systems]',
        'Deployment Architecture': '[Infrastructure approach, hosting strategy - ONLY for infrastructure-heavy projects]',
        'CLI Commands': '[Command interface design - ONLY for CLI tools]',
    },
    iteration=0,
    version=1,
    phase_status=PhaseStatus.DRAFT,
).build_markdown()


def generate_phase_command_template(tools: PhaseCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase-name] [optional: instructions]
description: Transform strategic plans into detailed Phases
---

# /respec-phase Command: Phase Creation

## Overview
Transform strategic plans into detailed Phases through quality-driven refinement. This command orchestrates technical architecture design, research integration, and platform-specific Phase storage.

## Primary Responsibilities

### 1. Initialize Technical Design Process
- Retrieve strategic plan from previous `/respec-plan` phase
- Launch phase-architect agent for technical architecture development
- Initialize MCP refinement loop for Phase creation

### 2. Coordinate Architecture Development
- Guide phase-architect through technical design decisions
- Integrate existing documentation from archive scanning
- Identify external research requirements for knowledge gaps

### 3. Manage Quality Assessment Loop
- Pass Phases to phase-critic for FSDD framework evaluation
- Handle MCP Server refinement decisions based on quality scores
- Iterate until MCP Server determines Phase meets quality requirements

### 4. Phase Storage
- Store final Phase using configured storage tools
- Maintain platform-agnostic content structure
- Include research requirements section for future implementation

## Orchestration Pattern

```text
Main Agent (via /respec-phase)
    │
    ├── 1. Retrieve Strategic Plan
    │   └── Access plan from previous phase or user input
    │
    ├── 2. Technical Design Loop
    │   ├── Task: phase-architect (architecture + research identification)
    │   ├── Task: phase-critic (FSDD quality assessment → score)
    │   └── MCP: decide_loop_next_action(loop_id)
    │
    ├── 3. Handle Loop Decision
    │   ├── IF "refine" → Pass feedback to phase-architect
    │   ├── IF "complete" → Proceed to storage
    │   └── IF "user_input" → Request technical clarification
    │
    └── 4. Store Phase
        └── Platform tool to store Phase
```

{tools.mcp_tools_reference}

## Implementation Instructions

### Step 1: Extract Command Arguments and Locate Phase File

Parse command arguments and locate phase file using partial name:

#### Step 1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the plan name]
PHASE_NAME_PARTIAL = [second argument from command - partial phase name]
OPTIONAL_INSTRUCTIONS = [third argument if provided, otherwise empty string]

Read .respec-ai/config.json
PROJECT_NAME = config["project_name"]
```

#### Step 1.2: Search file system for matching phase files

```text
SPEC_GLOB_PATTERN = ".respec-ai/projects/{{PROJECT_NAME}}/respec-phases/{{PHASE_NAME_PARTIAL}}*.md"
SPEC_FILE_MATCHES = Glob(pattern=SPEC_GLOB_PATTERN)
```

#### Step 1.3: Handle multiple matches

```text
IF count(SPEC_FILE_MATCHES) == 0:
  ERROR: "No Phase files found matching '{{PHASE_NAME_PARTIAL}}' in project {{PROJECT_NAME}}"
  SUGGEST: "Verify the phase name or check .respec-ai/projects/{{PROJECT_NAME}}/respec-phases/"
  EXIT: Workflow terminated

ELIF count(SPEC_FILE_MATCHES) == 1:
  SPEC_FILE_PATH = SPEC_FILE_MATCHES[0]

ELSE:
  (Multiple matches - use interactive selection)
  Use AskUserQuestion tool to present options:
    Question: "Multiple phase files match '{{PHASE_NAME_PARTIAL}}'. Which one do you want to use?"
    Header: "Select Spec"
    multiSelect: false
    Options: [
      {{
        "label": "{{SPEC_FILE_MATCHES[0]}}",
        "description": "Use: {{SPEC_FILE_MATCHES[0]}}"
      }},
      {{
        "label": "{{SPEC_FILE_MATCHES[1]}}",
        "description": "Use: {{SPEC_FILE_MATCHES[1]}}"
      }},
      ... for all matches
    ]

  SPEC_FILE_PATH = [selected file path from AskUserQuestion response]
```

#### Step 1.4: Extract canonical name from file path

Extract: ".respec-ai/projects/X/respec-phases/phase-2a-neo4j-integration.md" → "phase-2a-neo4j-integration"

```text
PHASE_NAME = [basename of SPEC_FILE_PATH without .md extension]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PLAN_NAME identifies which strategic plan to use for context
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-2a")
- PHASE_NAME is the canonical name extracted from file path (e.g., "phase-2a-neo4j-schema-and-llama-index-integration")
- PROJECT_NAME from config is used for all MCP storage operations
- OPTIONAL_INSTRUCTIONS provides additional context for phase development
- All subsequent operations use PHASE_NAME (canonical)

### Step 2: Load and Store Existing Documents

Load phase and plan from file system, store in MCP:

#### Step 2.1: Read documents using canonical names

```text
PLAN_MARKDOWN = Read(.respec-ai/projects/{{PLAN_NAME}}/project_plan.md)
PHASE_MARKDOWN = Read({{SPEC_FILE_PATH}})
```

#### Step 2.2: Store in MCP using canonical phase name

```text
{tools.store_plan}
  project_name=PLAN_NAME,
  project_plan_markdown=PLAN_MARKDOWN
)

{tools.store_document_inline_doc}
{tools.store_document}
  doc_type="phase",
  path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
  content=PHASE_MARKDOWN
)

Display to user: "✓ Loaded existing phase: {{PHASE_NAME}}"
```

**Important**:
- SPEC_FILE_PATH is the full path from Step 1
- PHASE_NAME is the canonical name extracted from file path
- Both documents are now in MCP storage for refinement loop

### Step 4: Initialize Refinement Loop
Initialize MCP refinement loop and retrieve strategic plan:

```text
(Initialize MCP refinement loop)
{tools.initialize_refinement_loop_inline_doc}
{tools.initialize_loop}
  project_name=PROJECT_NAME,
  loop_type="phase"
)

(Retrieve strategic plan using PLAN_NAME argument)
STRATEGIC_PLAN_MARKDOWN = {tools.get_plan})

IF STRATEGIC_PLAN_MARKDOWN not found:
  ERROR: "No strategic plan found: [PLAN_NAME]"
  SUGGEST: "Run '/respec-plan [PLAN_NAME]' to create strategic plan first"
  EXIT: Graceful failure with guidance
```

### Step 4.2: Link Loop to Phase

After initializing loop, link it to Phase for idempotent retrieval:

```text
(Extract loop_id from initialize_refinement_loop result)
LOOP_ID = [loop_id from Step 4.1 MCPResponse]

(Validate loop_id was returned)
IF LOOP_ID is None or LOOP_ID == "":
    CRITICAL ERROR: "initialize_refinement_loop did not return valid loop_id"
    DIAGNOSTIC: Show full MCPResponse from Step 4.1
    EXIT: Workflow terminated

(Link loop to phase for agents to retrieve via loop_id only)
{tools.link_loop_to_document_inline_doc}
{tools.link_loop}
  loop_id=LOOP_ID,
  doc_type="phase",
  path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}"
)

(Verify the link was created)
LOOP_STATUS = {tools.get_loop_status})

IF LOOP_STATUS does not show linked phase:
    CRITICAL ERROR: "Loop linking failed - phase-architect and phase-critic will fail"
    DIAGNOSTIC: Show LOOP_STATUS details
    EXIT: Workflow terminated

Display to user: "✓ Refinement loop {{LOOP_ID}} linked to {{PHASE_NAME}}"
```

**Important**:
- loop_id MUST be extracted and validated before proceeding
- Agents depend on this link - fail loudly if it's broken
- Empty string "" is NOT valid - only non-empty string or None

### Step 5: Launch Architecture Development
Begin technical design with archive integration:

```text
(Execute archive scanning first)
ARCHIVE_SCAN_RESULTS = Bash: ~/.claude/scripts/research-advisor-archive-scan.sh "technical architecture design patterns database integration API security"

(Populate context variables from Step 4 output)
STRATEGIC_PLAN_SUMMARY = [strategic plan content: STRATEGIC_PLAN_MARKDOWN retrieved in Step 4]

(Invoke phase-architect agent)
Invoke: respec-phase-architect
Input:
  - loop_id: LOOP_ID
  - project_name: PROJECT_NAME
  - phase_name: PHASE_NAME
  - strategic_plan_summary: STRATEGIC_PLAN_SUMMARY
  - optional_instructions: OPTIONAL_INSTRUCTIONS
  - archive_scan_results: ARCHIVE_SCAN_RESULTS
  # No previous_feedback - architect retrieves feedback directly from MCP using loop_id

Agent will:
1. Retrieve current phase from MCP using loop_id
2. Retrieve previous critic feedback from MCP (if iteration > 1)
3. Refine phase based on strategic plan, feedback, and archive insights
4. Store updated phase directly in MCP
5. Return brief status message (no full markdown)

Verify agent completed successfully:
IF agent returns error status:
  ERROR: "phase-architect failed to update Phase"
  DIAGNOSTIC: Check agent logs for MCP tool call failures
  EXIT: Workflow terminated

Display to user: "✓ Phase refined by phase-architect"
```

### Step 6: Quality Assessment Loop

#### Step 6.1: Invoke Spec-Critic Agent

```text
Invoke: respec-phase-critic
Input:
  - project_name: PROJECT_NAME
  - loop_id: LOOP_ID
  - phase_name: PHASE_NAME

Spec-critic will:
1. Retrieve phase from MCP using project_name and phase_name
2. Evaluate against FSDD framework
3. Store feedback in MCP loop using loop_id
```

#### Step 6.2: Get Loop Decision

**MCP Server handles score extraction and loop decision internally.**

```text
LOOP_DECISION_RESPONSE = {tools.decide_loop_action})
(Returns: {{status: "COMPLETE|REFINE|USER_INPUT", loop_id: "abc123", iteration: N}})

LOOP_DECISION = LOOP_DECISION_RESPONSE.status

Note: No need to retrieve feedback or score - phase-critic stored feedback in MCP,
and MCP automatically recorded score and computed loop decision.
```

### Step 7: Handle Refinement Decisions

**Follow LOOP_DECISION exactly. Do not override based on score assessment.**

```text
IF LOOP_DECISION == "COMPLETE":
  Display to user: "✓ Phase meets quality standards"
  Proceed to Step 8.

ELIF LOOP_DECISION == "REFINE":
  Display to user: "⟳ Refining Phase - phase-architect will address critic feedback"
  Return to Step 5 (phase-architect will retrieve feedback from MCP itself)

ELIF LOOP_DECISION == "USER_INPUT":
  (Check for Decomposition Requirement)
  LATEST_FEEDBACK = {tools.get_feedback})

  IF "DECOMPOSITION_REQUIRED" in LATEST_FEEDBACK or "SCOPE_CREEP" in LATEST_FEEDBACK:
    Display to user:

    ⚠️ DECOMPOSITION REQUIRED ⚠️

    The Phase is too broad for a single implementation phase.

    Current Size: [Extract character count from LATEST_FEEDBACK]
    Recommended: Break into 3-5 focused phases

    **Next Steps:**
    1. Run: /respec-roadmap [PROJECT_NAME]
    2. This will analyze the current phase and create multiple smaller phases
    3. Each resulting phase will be appropriately scoped

    **Alternative** (not recommended):
    - Manually condense the phase to <40,000 characters
    - Provide technical clarification via user feedback
    - Resume refinement loop

    EXIT: Graceful stop with guidance

  ELSE:
    (Regular USER_INPUT handling for stagnation or checkpoint)
    Display LATEST_FEEDBACK to user with:
    - Current score and iteration
    - Priority improvement areas
    - Request for technical clarification

    Return to Step 5 (phase-architect will incorporate user guidance)

ELIF LOOP_DECISION == "MAX_ITERATIONS":
  Display warning: "Maximum iterations reached. Review feedback and decide next steps."
  Display LATEST_FEEDBACK to user
  Proceed to Step 8.
```

### Step 8: Phase Storage

#### Step 8.1: Retrieve Final Phase from MCP
Retrieve the Phase from MCP storage:

```text
FINAL_PHASE_RESPONSE = {tools.get_document}
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}"
)

FINAL_PHASE_MARKDOWN = FINAL_PHASE_RESPONSE.message
```

#### Step 8.2: Save to External Platform
Store the phase using platform-specific tool:

```text
Use {tools.create_phase_tool_interpolated} to store the phase:

Title: Phase: [Project Name]
Content: [FINAL_PHASE_MARKDOWN]
Labels: phase, architecture, phase-2
```

**Important**: Use FINAL_PHASE_MARKDOWN from MCP, NOT raw architect output. This ensures immutable initial fields (objectives, scope, dependencies, deliverables) are preserved.

## Quality Assessment

### Loop Management
- Quality evaluation performed by phase-critic agent using FSDD framework
- Loop continuation decisions made by MCP Server based on configuration
- MCP Server monitors score improvement and iteration limits
- User input requested when stagnation detected

### Loop Decision Types
- **refine**: Continue refinement with critic feedback
- **complete**: Phase meets quality requirements
- **user_input**: Stagnation detected, user guidance needed
- **max_iterations**: Iteration limit reached

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
    "error_message": "No strategic plan found for Phase creation",
    "recovery_action": "Prompting user for plan location or /respec-plan execution",
    "user_guidance": "Please provide the strategic plan document path or run /respec-plan command first",
    "partial_output": "Phase template prepared"
  }}
  → Request plan location OR suggest: "Run /respec-plan [project-name] to create strategic plan first"
```

#### 2. Archive Scanning Failure
```text
IF ~/.claude/scripts/research-advisor-archive-scan.sh fails:
  ERROR_RESPONSE = {{
    "error_type": "archive_failure",
    "error_message": "Cannot access best-practices archive for pattern identification",
    "recovery_action": "Continuing with external research only, noting archive unavailable",
    "user_guidance": "Archive unavailable - all research will be external. Phase will include comprehensive research requirements.",
    "partial_output": "Strategic plan analysis completed"
  }}
  → Continue with phase-architect but include note: "Archive unavailable - comprehensive external research required"
```

#### 3. MCP Loop State Errors
```text
IF mcp__respec-ai__* tools unavailable:
  ERROR_RESPONSE = {{
    "error_type": "mcp_error",
    "error_message": "MCP loop state management unavailable",
    "recovery_action": "Falling back to direct agent coordination with single iteration",
    "user_guidance": "Quality loop disabled - single-pass Phase generation",
    "partial_output": "Strategic plan processed"
  }}
  → Continue with single phase-architect → phase-critic → storage workflow
```

#### 4. Storage Platform Failure
```text
IF platform storage tool fails:
  ERROR_RESPONSE = {{
    "error_type": "storage_failure",
    "error_message": "Failed to store Phase in configured platform",
    "recovery_action": "Saving to local Markdown backup at docs/respec-phases/[timestamp]-phase.md",
    "user_guidance": "Platform storage failed. Phase saved locally. Check platform connectivity and configuration.",
    "partial_output": "Complete Phase document"
  }}
  → Use Write tool to save to local file system as fallback
```

#### 5. Quality Plateau/Stagnation
```text
IF LOOP_DECISION == "user_input" (stagnation detected):
  ERROR_RESPONSE = {{
    "error_type": "quality_plateau",
    "error_message": "Phase quality plateaued at [QUALITY_SCORE]% after [CURRENT_ITERATION] iterations",
    "recovery_action": "Escalating to user for guidance on technical clarifications",
    "user_guidance": "Quality plateau reached. Please provide: 1) Technical clarifications, 2) Alternative approaches, 3) Accept current quality level",
    "partial_output": "Phase at [QUALITY_SCORE]% completeness"
  }}
```

### Proactive Error Prevention
- Validate strategic plan format before processing
- Check archive accessibility before scanning  
- Test MCP tool availability before loop initialization
- Verify storage platform connectivity before final storage
- Monitor quality score trends for early stagnation detection

## Phase Name Normalization Rules

**IMPORTANT:** Phase names are automatically normalized to kebab-case:

**File System → MCP Normalization:**
- Convert to lowercase: `Phase-1` → `phase-1`
- Replace spaces/underscores with hyphens: `phase 1` → `phase-1`
- Remove special characters: `phase-1!` → `phase-1`
- Collapse multiple hyphens: `phase--1` → `phase-1`
- Strip leading/trailing hyphens: `-phase-1-` → `phase-1`

**Critical:** The H1 header in phase markdown MUST match the normalized file name:
- File: `phase-2a-neo4j-schema-and-llama-index-integration.md`
- H1 header: `# Phase: phase-2a-neo4j-schema-and-llama-index-integration`
- Mismatch will cause storage/retrieval failures

**Phase-architect agents:** Generate H1 headers in kebab-case to match file names.

## Expected Output Structure

**CRITICAL**: Phase must follow exact H2 > H3 nesting for core sections. Phase name MUST be kebab-case (lowercase, hyphens only).

### Structure Template

```markdown
{technical_phase_template}
```

### Structure Rules

**For Core Sections** (Overview, System Design, Implementation, Additional Details):
- Always use H2 `##` for main section
- Always use H3 `###` for subsections
- Parser expects this exact structure - deviations cause field to be None

**For Domain-Specific Sections** (Data Models, API Design, etc.):
- Use H2 `##` for section header
- No required subsection structure
- Content captured in additional_sections dict

**Common Mistakes to Avoid**:
- ❌ Using "## Architecture" instead of "## System Design\n### Architecture"
- ❌ Using "## Research Requirements" instead of "## Additional Details\n### Research Requirements"
- ❌ Using H4 `####` or H5 `#####` for core subsections
- ❌ Omitting H2 section header (e.g., just "### Architecture" without "## System Design")

**Notes**:
- Core sections (Overview, Architecture, Testing Strategy) should always be present
- Domain-specific sections should only be included if relevant to the project type
- No placeholder content ("TBD", "N/A") - omit sections instead
- Content can use any markdown format (code blocks, lists, tables, diagrams)

## Context Preservation

Maintain conversation flow while processing complex backend refinement:
- Complete conversation history passed to each agent invocation
- Technical assessments hidden from user interaction  
- Natural dialogue flow preserved despite multi-agent coordination
- Context summarization to manage size constraints

## Implementation Integration Notes

### Phase Tools
- **Storage Tool**: Platform-specific creation tool
- **Retrieval Tool**: Platform-specific retrieval tool
- **Update Tool**: Platform-specific update tool
- **Content Structure**: Platform-agnostic markdown maintained consistently
- **Research Section**: Included in Phase body for all platforms

## Success Metrics

### Quantitative Targets
- **Quality Score**: Determined by MCP Server configuration
- **Iterations to Complete**: ≤3
- **Archive Hit Rate**: >60% of research needs covered by existing docs
- **Storage Success**: >99%

### Qualitative Indicators
- **Technical Completeness**: All architectural decisions documented
- **Research Coverage**: All knowledge gaps identified with clear paths
- **Implementation Ready**: Sufficient detail for development teams
- **Integration**: Seamless storage and retrieval

The Phase is ready for implementation planning. Recommend `/respec-code` command for next phase.
"""
