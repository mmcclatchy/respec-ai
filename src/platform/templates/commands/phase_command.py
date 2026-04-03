from textwrap import indent

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
    implementation_plan_references=(
        'Pre-resolved architecture decisions that MUST be honored.\n\n'
        '- Constraint: `<plans-dir>/<plan-name>.md` § "Section Name"\n'
        '  (brief rationale for why this constraint exists)'
    ),
    research_requirements=(
        '**Existing Documentation**:\n'
        '- Read: [paths to .best-practices/ docs]\n\n'
        '**External Research Needed**:\n'
        '- Synthesize: [research prompts with technology names]'
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

# respec-phase Command: Phase Creation

## Overview
Transform strategic plans into detailed Phases through quality-driven refinement. This command orchestrates technical architecture design, research integration, and platform-specific Phase storage.

## Primary Responsibilities

### 1. Initialize Technical Design Process
- Retrieve strategic plan from previous `respec-plan` phase
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
Main Agent (via respec-phase)
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
```

#### Step 1.2: Search file system for matching phase files

```text
{tools.phase_discovery_instructions}
```

#### Step 1.3: Handle multiple matches

```text
IF count(SPEC_FILE_MATCHES) == 0:
  ERROR: "No Phase files found matching '{{PHASE_NAME_PARTIAL}}' in project {{PLAN_NAME}}"
  SUGGEST: "Verify the phase name or check {tools.phase_location_hint}"
  EXIT: Workflow terminated

ELIF count(SPEC_FILE_MATCHES) == 1:
  PHASE_FILE_PATH = PHASE_FILE_MATCHES[0]

ELSE:
  (Multiple matches - use interactive selection)
  Use AskUserQuestion tool to present options:
    Question: "Multiple phase files match '{{PHASE_NAME_PARTIAL}}'. Which one do you want to use?"
    Header: "Select Phase"
    multiSelect: false
    Options: [
      {{
        "label": "{{PHASE_FILE_MATCHES[0]}}",
        "description": "Use: {{PHASE_FILE_MATCHES[0]}}"
      }},
      {{
        "label": "{{PHASE_FILE_MATCHES[1]}}",
        "description": "Use: {{PHASE_FILE_MATCHES[1]}}"
      }},
      ... for all matches
    ]

  PHASE_FILE_PATH = [selected file path from AskUserQuestion response]
```

#### Step 1.4: Extract canonical name from file path

Extract: "{tools.phase_resource_example}" → "phase-2a-neo4j-integration"

```text
PHASE_NAME = [basename of PHASE_FILE_PATH without .md extension]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PLAN_NAME identifies which strategic plan to use for context
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-2a")
- PHASE_NAME is the canonical name extracted from file path (e.g., "phase-2a-neo4j-schema-and-llama-index-integration")
- PLAN_NAME from config is used for all MCP storage operations
- OPTIONAL_INSTRUCTIONS provides additional context for phase development
- All subsequent operations use PHASE_NAME (canonical)

### Step 2: Load and Store Existing Documents

Load phase and plan from file system, store in MCP:

#### Step 2.1: Sync plan document

```text
{tools.sync_plan_instructions}
```

#### Step 2.2: Sync phase document

```text
{tools.sync_phase_instructions}
```

**Important**:
- PHASE_FILE_PATH is the full path from Step 1
- PHASE_NAME is the canonical name extracted from file path
- Both documents are now in MCP storage for refinement loop

### Step 4: Initialize Refinement Loop
Initialize MCP refinement loop:

```text
(Initialize MCP refinement loop)
{tools.initialize_refinement_loop_inline_doc}
{tools.initialize_loop}
  plan_name=PLAN_NAME,
  loop_type="phase"
)
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
  key=f"{{PLAN_NAME}}/{{PHASE_NAME}}"
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
Begin technical design:

```text
{tools.invoke_phase_architect}

Agent will:
1. Retrieve strategic plan from MCP using plan_name
2. Execute archive scan to identify existing documentation
3. Retrieve current phase from MCP using loop_id
4. Retrieve previous critic feedback from MCP (if iteration > 1)
5. Refine phase based on strategic plan, feedback, and archive insights
6. Store updated phase directly in MCP
7. **Lifecycle Management**: If phase is being decomposed into sub-phases:
   - Original phase status MUST transition to SUPERSEDED
   - Each sub-phase MUST follow `phase-{{number}}-{{description}}` naming pattern
   - Dependencies between sub-phases MUST be documented in Dependencies section
   - VIOLATION: Leaving original phase as DRAFT when decomposed breaks downstream task-planner
8. Return brief status message (no full markdown)

Verify agent completed successfully:
IF agent returns error status:
  ERROR: "phase-architect failed to update Phase"
  DIAGNOSTIC: Check agent logs for MCP tool call failures
  EXIT: Workflow terminated

Display to user: "✓ Phase refined by phase-architect"
```

### Step 6: Quality Assessment Loop

#### Step 6.1: Invoke Phase-Critic Agent

{tools.invoke_phase_critic}

#### Step 6.2: Get Loop Decision

**MCP Server handles score extraction and loop decision internally.**

```text
LOOP_DECISION_RESPONSE = {tools.decide_loop_action})
LOOP_DECISION = LOOP_DECISION_RESPONSE.status
LOOP_SCORE = LOOP_DECISION_RESPONSE.current_score
LOOP_ITERATION = LOOP_DECISION_RESPONSE.iteration
```

### Step 7: Handle Refinement Decisions

═══════════════════════════════════════════════
MANDATORY DECISION PROTOCOL
═══════════════════════════════════════════════
The MCP decision is FINAL. Execute the matching branch IMMEDIATELY.

"refine"     → Execute refinement. Do NOT ask, confirm, or present options to the user.
"user_input" → ONLY status that involves the user. Present feedback and wait for response.
"complete"   → Proceed to next step. Do NOT ask for confirmation.

VIOLATION: Asking the user "Should I continue refining?" when status is "refine"
           is a workflow violation. The decision has already been made by the MCP server.
═══════════════════════════════════════════════

```text
IF LOOP_DECISION == "COMPLETE":
  Display to user: "✅ Score: {{LOOP_SCORE}}/100 — Phase meets quality standards"
  Proceed to Step 8.

ELIF LOOP_DECISION == "REFINE":
  Display to user: "⟳ Iteration {{LOOP_ITERATION}} · Score: {{LOOP_SCORE}}/100 — refining Phase"
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
    1. Run: respec-roadmap [PLAN_NAME]
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
  Proceed to Step 7.5.
```

### Step 7.5: Synthesize Research Requirements

After quality loop completes, synthesize any "Synthesize:" research prompts using best-practices-rag:

```text
SUB-STEP 1: Retrieve final phase
PHASE_RESPONSE = {tools.get_document}
    doc_type="phase",
    key="{{PLAN_NAME}}/{{PHASE_NAME}}",
    loop_id=LOOP_ID
)
PHASE_MARKDOWN = PHASE_RESPONSE.message

SUB-STEP 2: Parse Research Requirements
Extract "### Research Requirements" section from PHASE_MARKDOWN.
Collect:
- "Read:" entries → EXISTING_PATHS (keep as-is)
- "Synthesize:" entries → SYNTHESIZE_PROMPTS

IF no SYNTHESIZE_PROMPTS:
  Display: "✓ No research synthesis required"
  Proceed to Step 7.6.

SUB-STEP 3: Pre-compute bp-pipeline parameters for each prompt
For EACH prompt in SYNTHESIZE_PROMPTS:
  Extract TECH (technology names) and TOPICS (remaining keywords) from prompt text.

  Bash: best-practices-rag lookup-versions --tech "TECH"
  → Parse JSON: TECH_VERSIONS_JSON, CUTOFF_DATE

  Bash: best-practices-rag generate-slug --tech "TECH" --topics "TOPICS"
  → OUTPUT_SLUG = stdout
  → OUTPUT_FILE = ".best-practices/{{OUTPUT_SLUG}}-codegen.md"

  Bash: best-practices-rag check-file-cache --file "OUTPUT_FILE" --model "<model ID>"
  → IF hit is true: record OUTPUT_FILE in CACHED_PATHS, skip this prompt
  → IF hit is false: continue

  Bash: best-practices-rag query-kb --tech "TECH" --topics "TOPICS"
  → Parse count, staleness, coverage fields
  → Compute COVERED_TECHS, UNCOVERED_TECHS, STALE_CONTEXT_BODY

  Build PRIMARY_QUERY: versioned query with "official documentation"

  Store computed parameters for this prompt.

SUB-STEP 4: Launch bp-pipeline Tasks IN PARALLEL
For ALL uncached prompts, launch bp-pipeline agents simultaneously:

  Task(bp-pipeline):
  MODE: codegen
  TECH: <comma-separated tech names>
  QUERY: <original synthesize prompt>
  TECH_VERSIONS_JSON: <JSON from lookup-versions>
  CUTOFF_DATE: <from lookup-versions>
  PRIMARY_QUERY: <versioned query>
  OUTPUT_FILE: <computed path>
  TOPICS: <comma-separated topics>
  STALE_CONTEXT_BODY: <if any stale KB results, omit if none>
  STALE_TECHNOLOGIES: <if any, omit if none>
  VERSION_DELTAS: <if any, omit if none>
  UNCOVERED_TECH: <if partial gap, omit if full gap or full coverage>
  COVERED_TECHS: <if partial gap or cache hit, omit if full gap>
  ALL_QUERIED_TECHS: <tech names from prompt>

Wait for ALL tasks to return BP_PIPELINE_COMPLETE signals.

═══════════════════════════════════════════════
MANDATORY BP-PIPELINE VALIDATION GATE
═══════════════════════════════════════════════
IF any task does NOT return BP_PIPELINE_COMPLETE:
  ERROR: "bp-pipeline failed — research synthesis incomplete"
  DIAGNOSTIC: Show failed task names and error output
  EXIT: Do NOT proceed to SUB-STEP 5 with partial research

VIOLATION: Displaying bp-pipeline error but continuing to update
           the phase with incomplete research paths.
═══════════════════════════════════════════════

SUB-STEP 5: Update Phase with synthesized paths
SYNTHESIZED_PATHS = paths from BP_PIPELINE_COMPLETE signals + CACHED_PATHS
COMPLETE_PATHS = EXISTING_PATHS + SYNTHESIZED_PATHS

Reconstruct Research Requirements section with ONLY "Read:" entries:
For each PATH in COMPLETE_PATHS:
  "- Read: `{{PATH}}`"

Replace "### Research Requirements" section in PHASE_MARKDOWN with updated content.

SUB-STEP 6: Store updated Phase
{tools.store_document}
  doc_type="phase",
  key="{{PLAN_NAME}}/{{PHASE_NAME}}",
  content=UPDATED_PHASE_MARKDOWN
)

Display: "✓ Synthesized {{len(SYNTHESIZED_PATHS)}} research brief(s), {{len(COMPLETE_PATHS)}} total documents"

Proceed to Step 7.6.
```

### Step 7.6: Post-Synthesis Quality Validation

After research synthesis completes, validate all research paths exist:

```text
Display to user: "🔍 Validating synthesized research paths..."

{tools.invoke_phase_critic}

IF validation_result shows invalid_count > 0:
    Display warning: "⚠️ Synthesized research paths invalid:"
    List INVALID_PATHS
    Display: "Check bp-pipeline output logs"
    # Non-blocking - user can proceed
ELSE:
    Display: "✓ All research paths validated successfully"

Proceed to Step 8.
```

### Step 8: Phase Storage

═══════════════════════════════════════════════
MANDATORY PHASE FILE STORAGE RESTRICTION
═══════════════════════════════════════════════
Phase storage uses ONLY these two mechanisms:
1. MCP storage (already completed during refinement loop)
2. Platform storage (Step 8.2 below)

Do NOT:
- Write phase.md or any .md file to disk directly
- Create backup or checkpoint files
- Store intermediate phases outside MCP/platform

VIOLATION: Writing any phase file outside the designated
           MCP and platform storage tools.
═══════════════════════════════════════════════

#### Step 8.1: Retrieve Final Phase from MCP
Retrieve the Phase from MCP storage:

```text
FINAL_PHASE_RESPONSE = {tools.get_document}
    doc_type="phase",
    key=f"{{PLAN_NAME}}/{{PHASE_NAME}}"
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

### Knowledge Base Scanning Process
Knowledge base scanning performed via `best-practices-rag query-kb` and `Glob: .best-practices/*.md` to identify existing documentation and knowledge gaps for research requirements section.

### Research Requirements Format
  ```markdown
  ## Research Requirements

  ### Existing Documentation
  - Read: .best-practices/react-hooks-patterns-codegen.md
  - Read: .best-practices/postgresql-optimization-codegen.md

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
    "recovery_action": "Prompting user for plan location or respec-plan execution",
    "user_guidance": "Please provide the strategic plan document path or run respec-plan command first",
    "partial_output": "Phase template prepared"
  }}
  → Request plan location OR suggest: "Run respec-plan [plan-name] to create strategic plan first"
```

#### 2. Knowledge Base Query Failure
```text
IF best-practices-rag query-kb fails:
  ERROR_RESPONSE = {{
    "error_type": "kb_query_failure",
    "error_message": "Cannot query best-practices knowledge base",
    "recovery_action": "Continuing with external research only, noting KB unavailable",
    "user_guidance": "Knowledge base unavailable - check Docker and Neo4j status via `best-practices-rag check`. Phase will include comprehensive research requirements.",
    "partial_output": "Strategic plan analysis completed"
  }}
  → Continue with phase-architect but include note: "Knowledge base unavailable - comprehensive external research required"
```

#### 3. MCP Loop State Errors
```text
IF mcp__respec-ai tools unavailable:
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
    "recovery_action": "Saving to local Markdown backup at docs/phases/[timestamp]-phase.md",
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
{indent(technical_phase_template, '  ')}
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
- Core sections (Overview, Architecture, Testing Strategy) MUST always be present
- Domain-specific sections MUST only be included if relevant to the project type
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

## Step 9: Automatic Task Generation

After Phase storage completes, automatically generate the Task document:

```text
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Display: "✅  PHASE COMPLETE — generating Task document"
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

Invoke the task command to generate the Task with full quality loop:

{tools.task_command_invocation}

The `respec-task` command will:
1. Locate the Phase file on disk
2. Initialize a task quality loop
3. Run task-planner → task-plan-critic refinement cycle
4. Store the Task document to MCP and platform

**If respec-task fails**: The Phase is already stored and valid. Display:
```text
"⚠ Task generation failed. Phase is saved. Run respec-task {{PLAN_NAME}} {{PHASE_NAME}} manually."
```

**After respec-task completes**: Display next steps:
```text
"✅ Phase and Task complete. Next: respec-code {{PLAN_NAME}} {{PHASE_NAME}}"
```

The Phase and Task are ready for implementation. Recommend `respec-code` command for next step.
"""
