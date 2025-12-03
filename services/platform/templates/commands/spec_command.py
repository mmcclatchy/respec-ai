from services.models.enums import SpecStatus
from services.models.spec import TechnicalSpec
from services.platform.models import SpecCommandTools


# Create template instance with instructional placeholders
technical_spec_template = TechnicalSpec(
    phase_name='[spec-name-in-kebab-case]',
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
    spec_status=SpecStatus.DRAFT,
).build_markdown()


def generate_spec_command_template(tools: SpecCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [spec-name] [optional: instructions]
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
- Iterate until MCP Server determines specification meets quality requirements

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

### Step 1: Extract Command Arguments and Locate Spec File

Parse command arguments and locate spec file using partial name:

```text
# Step 1.1: Parse arguments
PLAN_NAME = [first argument from command - the plan name]
SPEC_NAME_PARTIAL = [second argument from command - partial spec name]
OPTIONAL_INSTRUCTIONS = [third argument if provided, otherwise empty string]

Read .specter/config.json
PROJECT_NAME = config["project_name"]

# Step 1.2: Search file system for matching spec files
SPEC_GLOB_PATTERN = ".specter/projects/{{PROJECT_NAME}}/specter-specs/{{SPEC_NAME_PARTIAL}}*.md"
SPEC_FILE_MATCHES = Glob(pattern=SPEC_GLOB_PATTERN)

# Step 1.3: Handle multiple matches
IF count(SPEC_FILE_MATCHES) == 0:
  ERROR: "No specification files found matching '{{SPEC_NAME_PARTIAL}}' in project {{PROJECT_NAME}}"
  SUGGEST: "Verify the spec name or check .specter/projects/{{PROJECT_NAME}}/specter-specs/"
  EXIT: Workflow terminated

ELIF count(SPEC_FILE_MATCHES) == 1:
  SPEC_FILE_PATH = SPEC_FILE_MATCHES[0]

ELSE:
  # Multiple matches - use interactive selection
  Use AskUserQuestion tool to present options:
    Question: "Multiple spec files match '{{SPEC_NAME_PARTIAL}}'. Which one do you want to use?"
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

# Step 1.4: Extract canonical name from file path
# Extract: ".specter/projects/X/specter-specs/phase-2a-neo4j-integration.md" → "phase-2a-neo4j-integration"
SPEC_NAME = [basename of SPEC_FILE_PATH without .md extension]

Display to user: "✓ Located spec file: {{SPEC_NAME}}"
```

**Important**:
- PLAN_NAME identifies which strategic plan to use for context
- SPEC_NAME_PARTIAL is the user input (e.g., "phase-2a")
- SPEC_NAME is the canonical name extracted from file path (e.g., "phase-2a-neo4j-schema-and-llama-index-integration")
- PROJECT_NAME from config is used for all MCP storage operations
- OPTIONAL_INSTRUCTIONS provides additional context for spec development
- All subsequent operations use SPEC_NAME (canonical)

### Step 2: Load and Store Existing Documents

Load spec and plan from file system, store in MCP:

```text
# Step 2.1: Read documents using canonical names
PLAN_MARKDOWN = Read(.specter/projects/{{PLAN_NAME}}/project_plan.md)
SPEC_MARKDOWN = Read({{SPEC_FILE_PATH}})

# Step 2.2: Store in MCP using canonical spec name
mcp__specter__store_project_plan(
  project_name=PLAN_NAME,
  project_plan_markdown=PLAN_MARKDOWN
)

mcp__specter__store_spec(
  project_name=PROJECT_NAME,
  spec_name=SPEC_NAME,
  spec_markdown=SPEC_MARKDOWN
)

Display to user: "✓ Loaded existing spec: {{SPEC_NAME}}"
```

**Important**:
- SPEC_FILE_PATH is the full path from Step 1
- SPEC_NAME is the canonical name extracted from file path
- Both documents are now in MCP storage for refinement loop

### Step 3: Verify Canonical Spec Name

Verify spec is correctly stored in MCP with canonical name:

```text
# Call resolve_spec_name for validation only
RESOLVE_RESULT = mcp__specter__resolve_spec_name(
  project_name=PROJECT_NAME,
  partial_name=SPEC_NAME
)

IF RESOLVE_RESULT['count'] != 1:
  ERROR: "Spec storage validation failed - expected 1 match for '{{SPEC_NAME}}', got {{RESOLVE_RESULT['count']}}"
  DIAGNOSTIC: Check that Step 2 (Load and Store) completed successfully
  EXIT: Workflow terminated

# Validation passed - canonical name matches MCP storage
Display to user: "✓ Using specification: {{SPEC_NAME}}"
```

**Important**:
- resolve_spec_name is now used for VALIDATION only, not resolution
- Confirms storage succeeded with correct canonical name from Step 1
- Fails loudly if mismatch between file system and MCP

### Step 4: Initialize Refinement Loop
Initialize MCP refinement loop and retrieve strategic plan:

```text
# Initialize MCP refinement loop
mcp__specter__initialize_refinement_loop:
  loop_type: "spec"

# Retrieve strategic plan using PLAN_NAME argument
STRATEGIC_PLAN_MARKDOWN = mcp__specter__get_project_plan_markdown(project_name=PLAN_NAME)

IF STRATEGIC_PLAN_MARKDOWN not found:
  ERROR: "No strategic plan found: [PLAN_NAME]"
  SUGGEST: "Run '/specter-plan [PLAN_NAME]' to create strategic plan first"
  EXIT: Graceful failure with guidance
```

### Step 4.2: Link Loop to Specification

After initializing loop, link it to specification for idempotent retrieval:

```text
# Extract loop_id from initialize_refinement_loop result
LOOP_ID = [loop_id from Step 4.1 MCPResponse]

# Validate loop_id was returned
IF LOOP_ID is None or LOOP_ID == "":
    CRITICAL ERROR: "initialize_refinement_loop did not return valid loop_id"
    DIAGNOSTIC: Show full MCPResponse from Step 4.1
    EXIT: Workflow terminated

# Link loop to spec for agents to retrieve via loop_id only
mcp__specter__link_loop_to_spec(
  loop_id=LOOP_ID,
  project_name=PROJECT_NAME,
  spec_name=SPEC_NAME
)

# Verify the link was created
LOOP_STATUS = mcp__specter__get_loop_status(loop_id=LOOP_ID)

IF LOOP_STATUS does not show linked spec:
    CRITICAL ERROR: "Loop linking failed - spec-architect and spec-critic will fail"
    DIAGNOSTIC: Show LOOP_STATUS details
    EXIT: Workflow terminated

Display to user: "✓ Refinement loop {{LOOP_ID}} linked to {{SPEC_NAME}}"
```

**Important**:
- loop_id MUST be extracted and validated before proceeding
- Agents depend on this link - fail loudly if it's broken
- Empty string "" is NOT valid - only non-empty string or None

### Step 5: Launch Architecture Development
Begin technical design with archive integration:

```text
# Execute archive scanning first
ARCHIVE_SCAN_RESULTS = Bash: ~/.claude/scripts/research-advisor-archive-scan.sh "technical architecture design patterns database integration API security"

# Populate context variables from Step 4 output
STRATEGIC_PLAN_SUMMARY = [strategic plan content: STRATEGIC_PLAN_MARKDOWN retrieved in Step 4]

# Invoke spec-architect agent
Invoke: specter-spec-architect
Input:
  - loop_id: LOOP_ID
  - project_name: PROJECT_NAME
  - spec_name: SPEC_NAME
  - strategic_plan_summary: STRATEGIC_PLAN_SUMMARY
  - optional_instructions: OPTIONAL_INSTRUCTIONS
  - archive_scan_results: ARCHIVE_SCAN_RESULTS
  - previous_feedback: CRITIC_FEEDBACK (if this is a refinement iteration)

Agent will:
1. Retrieve current spec from MCP using loop_id
2. Refine spec based on strategic plan and feedback
3. Store updated spec directly in MCP
4. Return brief status message (no full markdown)

Verify agent completed successfully:
IF agent returns error status:
  ERROR: "spec-architect failed to update specification"
  DIAGNOSTIC: Check agent logs for MCP tool call failures
  EXIT: Workflow terminated

Display to user: "✓ Specification refined by spec-architect"
```

### Step 6: Quality Assessment Loop

#### Step 6a: Invoke Spec-Critic Agent

```text
Invoke: specter-spec-critic
Input:
  - project_name: PROJECT_NAME
  - loop_id: LOOP_ID
  - spec_name: SPEC_NAME

Spec-critic will:
1. Retrieve spec from MCP using project_name and spec_name
2. Evaluate against FSDD framework
3. Store feedback in MCP loop using loop_id
```

#### Step 6b: Get Feedback and Extract Score

```text
CRITIC_FEEDBACK = mcp__specter__get_feedback(loop_id=LOOP_ID, count=2)
Note: Retrieves 2 most recent iterations for stagnation detection

Extract QUALITY_SCORE from CRITIC_FEEDBACK markdown
```

#### Step 6c: Validate Quality Assessment Feedback

After spec-critic completes, verify feedback was stored:

```text
# Retrieve feedback to confirm storage
STORED_FEEDBACK = mcp__specter__get_feedback(
  loop_id=LOOP_ID,
  count=1
)

# Verify feedback contains quality score
IF STORED_FEEDBACK does NOT contain quality score:
  ERROR: "spec-critic claimed success but feedback was not stored"
  DIAGNOSTIC:
    - Check agent logs for store_critic_feedback call
    - Verify loop_id is valid via get_loop_status
  RECOVERY:
    - Report error to user
    - DO NOT proceed to loop decision
```

### Step 7: Handle Refinement Decisions

**Follow LOOP_DECISION exactly. Do not override based on score assessment.**

```text
LOOP_DECISION = mcp__specter__decide_loop_next_action(
  loop_id=LOOP_ID,
  current_score=QUALITY_SCORE
)
```

#### If LOOP_DECISION == "complete"
Proceed to Step 8.

#### If LOOP_DECISION == "refine"
Return to Step 5a with CRITIC_FEEDBACK as previous_feedback parameter.
Execute Steps 5b, 6a, 6b, and 7 again.

#### If LOOP_DECISION == "user_input"
Present QUALITY_SCORE and Priority Improvements to user.
Request technical clarification.
Return to Step 5a with combined feedback.
Execute Steps 5b, 6a, 6b, and 7 again.

#### If LOOP_DECISION == "max_iterations"
Display warning: "Final Quality Score: QUALITY_SCORE%, Remaining gaps: [list]"
Proceed to Step 8.

### Step 8: Specification Storage
Store the technical specification:

```text
Use {tools.create_spec_tool_interpolated} to store the technical specification:

Title: Technical Specification: [Project Name]
Content: [Complete technical specification with research requirements]
Labels: technical-specification, architecture, phase-2
```

## Quality Assessment

### Loop Management
- Quality evaluation performed by spec-critic agent using FSDD framework
- Loop continuation decisions made by MCP Server based on configuration
- MCP Server monitors score improvement and iteration limits
- User input requested when stagnation detected

### Loop Decision Types
- **refine**: Continue refinement with critic feedback
- **complete**: Specification meets quality requirements
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

## Spec Name Normalization Rules

**IMPORTANT:** Spec names are automatically normalized to kebab-case:

**File System → MCP Normalization:**
- Convert to lowercase: `Phase-1` → `phase-1`
- Replace spaces/underscores with hyphens: `phase 1` → `phase-1`
- Remove special characters: `phase-1!` → `phase-1`
- Collapse multiple hyphens: `phase--1` → `phase-1`
- Strip leading/trailing hyphens: `-phase-1-` → `phase-1`

**Critical:** The H1 header in spec markdown MUST match the normalized file name:
- File: `phase-2a-neo4j-schema-and-llama-index-integration.md`
- H1 header: `# Technical Specification: phase-2a-neo4j-schema-and-llama-index-integration`
- Mismatch will cause storage/retrieval failures

**Spec-architect agents:** Generate H1 headers in kebab-case to match file names.

## Expected Output Structure

**CRITICAL**: Spec must follow exact H2 > H3 nesting for core sections. Spec name MUST be kebab-case (lowercase, hyphens only).

### Structure Template

```markdown
{technical_spec_template}
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

### Specification Tools
- **Storage Tool**: Platform-specific creation tool
- **Retrieval Tool**: Platform-specific retrieval tool
- **Update Tool**: Platform-specific update tool
- **Content Structure**: Platform-agnostic markdown maintained consistently
- **Research Section**: Included in specification body for all platforms

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

The specification is ready for implementation planning. Recommend `/specter-build` command for next phase.
"""
