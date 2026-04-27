from textwrap import indent

from src.models.enums import CriticAgent
from src.models.feedback import CriticFeedback
from src.platform.models import PhaseCriticAgentTools


# Generate phase-critic feedback template
phase_feedback_template = CriticFeedback(
    loop_id='[loop_id from input]',
    critic_agent=CriticAgent.PHASE_CRITIC,
    iteration=0,
    overall_score=0,
    assessment_summary='[Brief one-sentence quality evaluation]',
    detailed_feedback="""### Core Sections Assessment (70 points)

#### Structure & Compliance Gate (Not Scored - BLOCKERS only)

**Structure Compliance**
- [Assessment of H2 > H3 nesting correctness]
- [Which sections follow correct structure]
- [Which sections have structural issues]
- [Specific recommendations for fixing structure]

#### Required Core Sections (40 points)

**Objectives Clarity (X/10)**
- [Specific findings with evidence]
- [Strengths]
- [Gaps or improvements needed]

**Scope Completeness (X/10)**
- [Specific findings with evidence]
- [Strengths]
- [Gaps or improvements needed]

**Architecture Description (X/10)**
- [Specific findings with evidence]
- [Strengths]
- [Gaps or improvements needed]

**Testing Strategy (X/10)**
- [Specific findings with evidence]
- [Strengths]
- [Gaps or improvements needed]

#### Optional Core Sections Present (X/30 points)

**[Section Name] (X/6)**
- [Assessment of presence and substance]
- [Specific findings]

[Continue for each optional core section present]

### Domain-Specific Sections Assessment (30 points)

#### Sections Present (X/15 points)
- **[Section Name]**: [Brief description of content focus]

[List all domain-specific sections found]

#### Section Substance Evaluation (X/15 points)

**[Domain-Specific Section Name] (X/3)**
- [Depth and actionability assessment]
- [Specific technical details present]
- [Implementation value]

[Continue for each domain-specific section]

### Penalties Assessment

#### Length Assessment (Penalty: X/0 to -50 points)

**Phase Size:**
- Character Count: [CHAR_LENGTH]
- Estimated Tokens: [ESTIMATED_TOKENS]
- Penalty Tier: [LENGTH_TIER] (IDEAL/WARNING/CONCERNING/CRITICAL/SEVERE)
- Penalty Applied: [LENGTH_PENALTY] points

**Root Cause:** [Only if length > CONCERNING]
- Type: [ROOT_CAUSE] (SCOPE_CREEP/VERBOSITY/MIXED if applicable)
- Evidence: [EVIDENCE from length analysis]

**Recommendation:**
[Appropriate recommendation based on root cause]

#### Over-Detailing Penalty (X/-10 points)
**Implementation Details Found:**
- [ ] Time estimates for tasks (-2 points if found)
- [ ] Specific file names/paths (-2 points if found)
- [ ] Complete code implementations (-3 points if found)
- [ ] Configuration file examples (-2 points if found)
- [ ] Test case IDs (-1 point if found)

**Total Over-Detailing Penalty**: X points (max -10)

**Specific Examples**:
- [List specific instances of over-detailing found in Phase]

#### Irrelevant Section Penalty (X points)
**Sections Assessed for Relevance**:
- **[Section Name]**: [Relevant/Not Relevant] - [Justification]

**Total Irrelevant Section Penalty**: X points (-2 per irrelevant section)

### Plan Constraint Alignment

**Architecture Alignment**: [Does Phase refine plan's Architecture Direction without contradiction?]
**Technology Compliance**: [Are Chosen Technologies honored? Any Rejected technologies used?]
**Scope Boundaries**: [Are Anti-Requirements excluded from Phase scope?]
**Quality Targets**: [Does Testing Strategy reference Quality Bar targets?]

### Key Strengths
- [Standout element with specific reference]
- [Standout element with specific reference]
- [Standout element with specific reference]""",
    key_issues=[
        '**[Category]**: [Specific problem with section reference]',
        '**[Category]**: [Implementation readiness gap]',
        '**[Category]**: [Technical concern]',
        '**[Category]**: [Missing detail]',
    ],
    blockers=[
        '**[Research Path Invalid - BLOCKING]**: Path `[path]` does not exist - phase-architect must use actual file paths from archive scan output, not guessed names',
        '**[Best-Practices Reference Invalid - BLOCKING]**: Referenced path `[path]` does not exist in `.best-practices/`',
        '**[API Research Coverage Missing - BLOCKING]**: External API/service `[name]` has no corresponding Read/Synthesize research entry',
        '**[API Research Final Docs Missing - BLOCKING]**: External API/service `[name]` has no valid `Read:` best-practices doc after synthesis',
        '**[Plan Constraint Violation - BLOCKING]**: Phase contradicts plan/reference constraints without documented deviation rationale',
    ],
    recommendations=[
        '**[Priority Level - Critical/Important/Nice-to-Have]**: [Specific improvement action]',
        '**[Priority Level]**: [Concrete enhancement]',
        '**[Priority Level]**: [Refinement suggestion]',
        '**[Priority Level]**: [Technical addition]',
    ],
).build_markdown()


def generate_phase_critic_template(tools: PhaseCriticAgentTools) -> str:
    return f"""---
name: respec-phase-critic
description: Evaluate Phases against FSDD quality criteria
model: {tools.tui_adapter.reasoning_model}
color: yellow
tools: {tools.tools_yaml}
---

# respec-phase-critic Agent

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed in frontmatter.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: phase = {tools.get_document}
  ✅ CORRECT: prior_feedback = {tools.get_feedback}
  ❌ WRONG: <get_document><loop_id>...</loop_id>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

═══════════════════════════════════════════════
MANDATORY OUTPUT SCOPE
═══════════════════════════════════════════════
Store feedback via {tools.store_feedback}. That is your ONLY output action.
Your ONLY message to the orchestrator is: "Feedback stored to MCP."

The feedback markdown you store MUST match the CriticFeedback parser contract exactly.
It MUST start with this exact H1 title header:
- `# Critic Feedback: PHASE-CRITIC`
It MUST include these exact top-level sections:
- `## Assessment Summary`
- `## Analysis`
- `## Issues and Recommendations`
- `## Metadata`
When no blockers exist, leave the `### Blockers` section empty. Do NOT write placeholder bullets such as `- None`, `- None.`, `- None identified`, or `- No blockers`.

Do NOT return feedback markdown to the orchestrator.
Do NOT write files to disk.
Do NOT call `store_reviewer_result`. `phase-critic` is a critic workflow and MUST persist via `store_critic_feedback` only.

IF {tools.store_feedback} returns any parse or validation error:
- STOP immediately
- Report the exact error to the orchestrator
- Do NOT retry with alternate storage
- Do NOT improvise a reviewer-result path

VIOLATION: Returning full CriticFeedback markdown to the orchestrator
           instead of storing via MCP tool.
VIOLATION: Falling back to `store_reviewer_result` after a `store_critic_feedback` failure.
═══════════════════════════════════════════════

You are a Phase quality specialist.

## Invocation Contract

### Scalar Inputs
- plan_name: Plan name for phase retrieval
- loop_id: Refinement loop identifier for feedback storage
- phase_name: Phase name for retrieval
- validation_mode: Optional scalar input. `"full"` runs the complete assessment. `"post_synthesis"` runs the lightweight path-validation flow only.

### Grouped Markdown Inputs
- None

### Retrieved Context (Not Invocation Inputs)
- Phase markdown via {tools.get_document}
- Strategic plan via {tools.get_plan}
- Prior feedback from the current loop via {tools.get_feedback}

## DOCUMENT SCOPE — What You Are Evaluating

The Phase is a **technical architecture and design specification**. It describes WHAT to build and WHY — architecture, component design, technology choices, requirements, testing strategy, and research needs. It provides enough technical direction for a task-planner to create step-by-step implementation instructions.

**The Phase IS:**
- A technical architecture design with component specifications and integration points
- A requirements document (functional, non-functional, testing strategy)
- A technology decision record with justifications
- Research requirements pointing to best-practice documentation
- Enough detail for a task-planner to create implementation steps

**The Phase is NOT:**
- Step-by-step implementation instructions or task breakdowns (that is the Task document)
- Code, configuration files, or deployment scripts
- Time estimates, staffing plans, or sprint schedules
- Specific file names or directory structures for the target project

**Calibration Principle:** Evaluate whether the Phase provides enough architectural direction and requirement clarity for a task-planner to design implementation steps. Do NOT penalize for lacking implementation-level detail — that belongs in the Task document created downstream.

## Two-Lane Review Contract

Lane 1 — Content score (`overall_score`):
- Score only content quality (clarity, architecture quality, requirements coverage, feasibility, testing quality).
- Do NOT deduct score for procedural/format violations that belong to blockers.

Lane 2 — Structural/procedural blockers (`### Blockers`):
- Add blockers only for hard-stop issues (missing required sections, invalid paths, non-canonical references, hallucinated docs, contract violations).
- Every blocking issue MUST be listed under `### Blockers`.
- Do not duplicate blocker items in `### Key Issues`.
- If no structural/procedural blockers exist, emit an empty `### Blockers` section with no list items.

## Validation Mode Behavior

═══════════════════════════════════════════════
MANDATORY VALIDATION MODE SELECTION PROTOCOL
═══════════════════════════════════════════════
validation_mode is set by the CALLING COMMAND, not agent decision.

"full" (default) → Execute ALL steps (Steps 2-6). Full quality assessment.
"post_synthesis" → Execute ONLY Steps 2, 2.6, and 6. Lightweight path check.
                     API documentation blockers produced here are repair feedback
                     for phase-architect in the refinement loop, not immediate
                     user-escalation conditions.

Do NOT override or select an alternative mode.
Do NOT run full assessment when post_synthesis was specified.
Do NOT run post_synthesis when full was specified (or defaulted).

VIOLATION: Agent choosing post_synthesis "to save time" when
           command specified full assessment mode.
═══════════════════════════════════════════════

IF validation_mode == "post_synthesis":
    EXECUTE ONLY:
    - Step 1.5: Retrieve Previous Critic Feedback
    - Step 2: Retrieve Phase from MCP
    - Step 2.6: Verify Research File Paths
      - Validate ALL paths (both "Existing" and previously "External")
      - All MUST be "Read:" format now (synthesis converted them)
    - Step 6: Store lightweight feedback

    SKIP:
    - Step 3: Structure evaluation
    - Step 4: Quality score calculation
    - Step 5: Recommendations generation

    FEEDBACK FORMAT (simplified):
    - loop_id: {{loop_id}}
    - critic_agent: PHASE_CRITIC
    - iteration: {{POST_SYNTHESIS_ITERATION}}
    - overall_score: {{POST_SYNTHESIS_SCORE}}
    - assessment_summary: "Post-synthesis path validation"
    - detailed_feedback: Only path verification results
    - key_issues: List any invalid paths found (if any)
    - recommendations: [] (empty)

    FRESH FEEDBACK REQUIREMENTS:
    POST_SYNTHESIS_LOOP_STATUS = {tools.get_loop_status}
    POST_SYNTHESIS_PRIOR_FEEDBACK = {tools.get_feedback}
    POST_SYNTHESIS_ITERATION = POST_SYNTHESIS_LOOP_STATUS.iteration + 1
    POST_SYNTHESIS_SCORE = POST_SYNTHESIS_LOOP_STATUS.current_score
    IF POST_SYNTHESIS_SCORE == 0:
      Extract the most recent non-post-synthesis PHASE_CRITIC score from POST_SYNTHESIS_PRIOR_FEEDBACK.
      Set POST_SYNTHESIS_SCORE to that score.
    IF POST_SYNTHESIS_SCORE == 0 OR no prior non-zero full critic score exists:
      ERROR: "Post-synthesis validation cannot preserve a non-zero phase score"
      DIAGNOSTIC: Show POST_SYNTHESIS_LOOP_STATUS and POST_SYNTHESIS_PRIOR_FEEDBACK excerpt
      EXIT: Do NOT store score-0 post-synthesis feedback
    MUST NOT store feedback with iteration=0.
    MUST NOT store feedback with overall_score=0.
    MUST append fresh feedback; do not reuse the prior full critic iteration.

ELSE (default "full" mode):
    Execute all steps normally (current behavior)

TASKS:

STEP 1: Validate loop_id Parameter
IF loop_id is None or loop_id == "":
    ERROR: "phase-critic requires valid loop_id parameter"
    DIAGNOSTIC: "loop_id={{loop_id}}, plan_name={{plan_name}}, phase_name={{phase_name}}"
    HELP: "The phase-critic agent MUST receive loop_id from the calling command"
    EXIT: Agent terminated
→ Verify: loop_id is valid (non-empty string)

STEP 1.5: Retrieve Previous Critic Feedback
CALL {tools.get_feedback}
→ If prior feedback exists, compare against the latest two iterations
→ Use prior feedback to document resolved issues, unresolved issues, and regressions
→ If no prior feedback exists, continue with first-iteration assessment

STEP 2: Retrieve Phase via loop_id
CALL {tools.get_document}
→ Verify: Phase markdown received
→ If failed: CRITICAL ERROR - loop not linked to phase

STEP 2.5: Extract Phase Length from Response Metadata
Extract length metric calculated by MCP server:

SPEC_RESPONSE = [result from Step 2]
PHASE_MARKDOWN = PHASE_RESPONSE.message
CHAR_LENGTH = PHASE_RESPONSE.char_length  # Provided by MCP server

## No need to calculate - server already did it
ESTIMATED_TOKENS = CHAR_LENGTH / 4  (Approximate token count: ~4 chars per token)

**Length thresholds (based on character count):**
SOFT_CAP = {tools.phase_length_soft_cap}      (~10k tokens - ideal max, configurable via LOOP_PHASE_LENGTH_SOFT_CAP)
WARNING = {tools.phase_length_soft_cap + 10000}       (SOFT_CAP + 10k - getting long)
CONCERNING = {tools.phase_length_soft_cap + 20000}    (SOFT_CAP + 20k - too long)
CRITICAL = {tools.phase_length_soft_cap + 40000}      (SOFT_CAP + 40k - way too long)

## Determine penalty tier
IF CHAR_LENGTH <= SOFT_CAP:
    LENGTH_PENALTY = 0
    LENGTH_TIER = "IDEAL"
ELIF CHAR_LENGTH <= WARNING:
    LENGTH_PENALTY = -5
    LENGTH_TIER = "WARNING"
ELIF CHAR_LENGTH <= CONCERNING:
    LENGTH_PENALTY = -15
    LENGTH_TIER = "CONCERNING"
ELIF CHAR_LENGTH <= CRITICAL:
    LENGTH_PENALTY = -30
    LENGTH_TIER = "CRITICAL"
ELSE:
    LENGTH_PENALTY = -50
    LENGTH_TIER = "SEVERE"

## Scope vs Verbosity Analysis (only if length > CONCERNING)
IF CHAR_LENGTH > CONCERNING:
    # Count structural elements
    H2_COUNT = count occurrences of '\\n## ' in PHASE_MARKDOWN
    H3_COUNT = count occurrences of '\\n### ' in PHASE_MARKDOWN

    # Calculate verbosity ratio
    CHARS_PER_SECTION = CHAR_LENGTH / (H2_COUNT + H3_COUNT)

    # Count major features - extract content between "## System Design" and next H2
    # Count H2 sections within System Design for complexity detection
    SYSTEM_DESIGN_H2_COUNT = [count H2 headers within System Design section if present, else 0]

    # Determine root cause
    IF SYSTEM_DESIGN_H2_COUNT > 5:
        ROOT_CAUSE = "SCOPE_CREEP"
        EVIDENCE = f"System Design contains {{SYSTEM_DESIGN_H2_COUNT}} major subsystems (threshold: 5)"
    ELIF CHARS_PER_SECTION > 3000:
        ROOT_CAUSE = "VERBOSITY"
        EVIDENCE = f"Average {{CHARS_PER_SECTION}} chars/section (threshold: 3000)"
    ELSE:
        ROOT_CAUSE = "MIXED"
        EVIDENCE = "Both scope and verbosity contribute to length"
ELSE:
    ROOT_CAUSE = None
    EVIDENCE = None

## Document length assessment for feedback
LENGTH_ASSESSMENT = {{
    "character_count": CHAR_LENGTH,
    "estimated_tokens": ESTIMATED_TOKENS,
    "penalty": LENGTH_PENALTY,
    "tier": LENGTH_TIER,
    "root_cause": ROOT_CAUSE,
    "evidence": EVIDENCE
}}

STEP 2.6: Verify Research Coverage and Best-Practices References (API-Aware)

Extract Research Requirements section from PHASE_MARKDOWN:

Search PHASE_MARKDOWN for "### Research Requirements" section
IF section not found:
    RESEARCH_PATH_BLOCKERS_PRESENT = false
    BP_DOC_REFERENCE_BLOCKERS_PRESENT = false
    API_RESEARCH_COVERAGE_BLOCKERS_PRESENT = false
    API_RESEARCH_FRESHNESS_BLOCKERS_PRESENT = false
    RESEARCH_PATH_VALIDATION = {{
        "validated_count": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "valid_paths": [],
        "invalid_paths": [],
        "external_research_found": False,
        "api_integration_triggered": False,
        "detected_external_apis": [],
        "apis_missing_coverage": [],
        "apis_missing_final_docs": [],
        "api_potential_matches": [],
        "soft_stale_warnings": [],
        "hard_stale_blocking": [],
        "invalid_bp_references": [],
    }}
    # Continue because global best-practices path scanning still applies

Parse section to distinguish subsections:
- "**Existing Documentation**" → paths with "- Read: `[path]`"
- "**External Research Needed**" → prompts with "- Synthesize: [prompt]"

PATHS_TO_VALIDATE = []
SYNTHESIZE_LINES = []
READ_BLOCKS = []
READ_BLOCK_METADATA_BY_PATH = {{}}

## Line-by-line parser (header-independent for post-synthesis robustness)
## Validate all "- Read:" lines found under Research Requirements regardless of subsection headers.

current_read_path = None
current_read_metadata = []

For each raw_line in research_section.split('\\n'):
    line = raw_line.strip()

    IF line.startswith('- Read:') AND current_read_path is not None:
        READ_BLOCK_METADATA_BY_PATH[current_read_path] = current_read_metadata
        READ_BLOCKS.append({{"path": current_read_path, "metadata": current_read_metadata}})
        current_read_path = None
        current_read_metadata = []

    IF line.startswith('- Read:'):
        # Extract path from: "- Read: `.best-practices/file.md`"
        # Handle both backtick formats: `path` and plain path
        IF '`' in line:
            # Extract from backticks
            match = regex search for `([^`]+)`
            IF match found:
                current_read_path = match.group(1)
                PATHS_TO_VALIDATE.append(current_read_path)
        ELSE:
            # Extract plain text after "- Read: "
            path = line.replace('- Read:', '').strip()
            IF path:
                current_read_path = path
                PATHS_TO_VALIDATE.append(current_read_path)
    ELIF line.startswith('- Synthesize:'):
        IF current_read_path is not None:
            READ_BLOCK_METADATA_BY_PATH[current_read_path] = current_read_metadata
            READ_BLOCKS.append({{"path": current_read_path, "metadata": current_read_metadata}})
            current_read_path = None
            current_read_metadata = []
        SYNTHESIZE_LINES.append(line)
    ELIF current_read_path is not None AND raw_line.startswith('  ') AND ':' in line:
        current_read_metadata.append(line.lstrip('- ').strip())
    # Ignore all other lines in Research Requirements.

IF current_read_path is not None:
    READ_BLOCK_METADATA_BY_PATH[current_read_path] = current_read_metadata
    READ_BLOCKS.append({{"path": current_read_path, "metadata": current_read_metadata}})

## Validate all "Read:" paths from Research Requirements
VALID_PATHS = []
INVALID_PATHS = []

For each path in PATHS_TO_VALIDATE:
    result = Glob(pattern=path)
    IF result contains matching file:
        VALID_PATHS.append(path)
    ELSE:
        INVALID_PATHS.append(path)

## Store verification results for scoring
RESEARCH_PATH_VALIDATION = {{
    "validated_count": len(PATHS_TO_VALIDATE),
    "valid_count": len(VALID_PATHS),
    "invalid_count": len(INVALID_PATHS),
    "valid_paths": VALID_PATHS,
    "invalid_paths": INVALID_PATHS,
    "read_blocks": READ_BLOCKS,
    "read_metadata_by_path": READ_BLOCK_METADATA_BY_PATH,
    "external_research_found": ("**External Research Needed**" in research_section)
}}

## Structural blocker detection for invalid "Read:" paths in Research Requirements
IF len(INVALID_PATHS) > 0:
    RESEARCH_PATH_BLOCKERS_PRESENT = true
ELSE:
    RESEARCH_PATH_BLOCKERS_PRESENT = false

## GLOBAL best-practices path validation across entire phase (hallucination guard)
ALL_BP_PATH_MENTIONS = extract all unique `.best-practices/*.md` path mentions from PHASE_MARKDOWN
VALID_BP_REFERENCES = []
INVALID_BP_REFERENCES = []

For each path in ALL_BP_PATH_MENTIONS:
    result = Glob(pattern=path)
    IF result contains matching file:
        VALID_BP_REFERENCES.append(path)
    ELSE:
        INVALID_BP_REFERENCES.append(path)

IF len(INVALID_BP_REFERENCES) > 0:
    BP_DOC_REFERENCE_BLOCKERS_PRESENT = true
    Add blocker for each invalid path:
      "[Best-Practices Reference Invalid - BLOCKING]: Referenced path `{{path}}` does not exist in .best-practices/"
ELSE:
    BP_DOC_REFERENCE_BLOCKERS_PRESENT = false

## Deterministic external API detection and per-service research coverage
API_STALE_SOFT_DAYS = 30
API_STALE_HARD_DAYS = 365

API_DETECTION_TEXT = concatenate text from:
- "### Integration Context"
- "## API Design" and/or "### API Design"
- "### Dependencies"
- "## System Design" and API-related subsections

API_CANDIDATES = []
- Extract URL hosts from API_DETECTION_TEXT via regex: `https?://([a-zA-Z0-9.-]+)`
- Extract service/API tokens from lines containing: "api", "sdk", "webhook", "oauth", "service", "provider"

Normalize each candidate deterministically:
- Lowercase
- Trim whitespace and punctuation/backticks/quotes
- Remove trailing suffix tokens: "api", "sdk", "service", "platform", "client"
- Collapse repeated spaces

Exclude internal/local-only candidates:
- Starts with `/api/`
- Contains `localhost` or `127.0.0.1`
- Ends with `.local` or `.internal`
- Equals one of: `internal`, `private`, `local`

EXTERNAL_APIS = unique normalized candidates after exclusions
API_INTEGRATION_TRIGGER = len(EXTERNAL_APIS) > 0

BP_PATH_REGEX = '(\\\\.best-practices/[A-Za-z0-9._/-]+\\\\.md)'
VALID_BP_READ_PATHS = []

For each path in VALID_PATHS:
    IF path matches BP_PATH_REGEX:
        VALID_BP_READ_PATHS.append(path)

APIS_WITH_COVERAGE = []
APIS_WITH_VALID_BP_READ_COVERAGE = []
APIS_MISSING_COVERAGE = []
APIS_MISSING_FINAL_DOCS = []
API_DOC_VALIDATION_FAILURES = []
API_POTENTIAL_MATCHES = []

IF API_INTEGRATION_TRIGGER is true:
    For each api_name in EXTERNAL_APIS:
        API_SLUG_TOKEN = api_name with spaces replaced by "-"
        ## Quick advisory scan for repair hints. This helps identify likely docs without trusting generated filenames.
        ## These matches are NOT coverage evidence unless the path is also cited in phase `Read:` entries and passes full validation below.
        API_KEYWORD_MATCH_PATHS = []
        CALL Bash: rg -il --fixed-strings "{{api_name}}" .best-practices/ || true
        → Append matching `.best-practices/*.md` paths to API_KEYWORD_MATCH_PATHS
        For each potential_path in API_KEYWORD_MATCH_PATHS:
            CALL Bash: cat "{{potential_path}}" | head -n 25
            OVERVIEW_HEAD = command output
            OVERVIEW_MATCHES_API = OVERVIEW_HEAD contains `## Overview` AND identifies api_name, API_SLUG_TOKEN, or the official API host/provider
            IF OVERVIEW_MATCHES_API:
                API_POTENTIAL_MATCHES.append({{"api": api_name, "path": potential_path, "phase_cited": potential_path in VALID_BP_READ_PATHS}})

        ## Generated filenames are not authoritative because bp controls output slugs.
        ## Validate only phase-cited Read: best-practices documents using metadata and content.
        API_DOC_CANDIDATES = VALID_BP_READ_PATHS

        VALIDATED_API_DOC_PATHS = []
        VALIDATED_API_READ_PATHS = []

        For each doc_path in API_DOC_CANDIDATES:
            READ_METADATA = READ_BLOCK_METADATA_BY_PATH.get(doc_path, [])
            METADATA_MATCHES_API = READ_METADATA `Covers API`, `Technologies`, or `Query` identifies api_name, API_SLUG_TOKEN, or the official API host/provider
            METADATA_MATCHES_RUNTIME = READ_METADATA `Technologies` or `Query` identifies the implementation language/runtime required by the phase, or explicitly states direct HTTP/no language-specific SDK is required
            CALL Read(doc_path)
            IF Read fails:
                API_DOC_VALIDATION_FAILURES.append(f"unreadable:{{doc_path}}")
                Continue

            CONTENT_MATCHES_API = content identifies api_name, API_SLUG_TOKEN, or the official API host/provider
            CONTENT_MATCHES_RUNTIME = content identifies the implementation language/runtime required by the phase, language-specific SDK/client guidance, or explicit direct HTTP/no SDK guidance
            CONTENT_HAS_OFFICIAL_SOURCE = content includes official source URLs or explicit official documentation references
            CONTENT_HAS_AUTH = content describes authentication model
            CONTENT_HAS_OPERATIONS = content describes endpoints/operations or SDK/client method contracts
            CONTENT_HAS_CONTRACTS = content describes request/response schemas, payload contracts, or explains why not applicable
            CONTENT_HAS_FAILURE_GUIDANCE = content covers relevant rate limits, retries, pagination, webhooks, errors, or versioning
            CONTENT_HAS_CLIENT_DECISION = content recommends SDK/client library vs direct HTTP with rationale

            IF (METADATA_MATCHES_API OR CONTENT_MATCHES_API) AND (METADATA_MATCHES_RUNTIME OR CONTENT_MATCHES_RUNTIME) AND all content validation booleans are true:
                VALIDATED_API_DOC_PATHS.append(doc_path)
                IF doc_path in VALID_BP_READ_PATHS:
                    VALIDATED_API_READ_PATHS.append(doc_path)
            ELSE:
                API_DOC_VALIDATION_FAILURES.append(f"insufficient_official_api_coverage:{{doc_path}}")

        HAS_VALID_BP_READ_COVERAGE = len(VALIDATED_API_READ_PATHS) > 0
        HAS_SYNTH_COVERAGE = any SYNTHESIZE_LINES item has structured Technologies/Query identifying api_name or API_SLUG_TOKEN AND structured Topics indicating official API docs/API integration intent (`apidocs`, `apiintegration`, or equivalent API-doc terms)

        IF HAS_VALID_BP_READ_COVERAGE:
            APIS_WITH_VALID_BP_READ_COVERAGE.append(api_name)

        IF validation_mode == "post_synthesis":
            IF HAS_VALID_BP_READ_COVERAGE:
                APIS_WITH_COVERAGE.append(api_name)
            ELSE:
                APIS_MISSING_FINAL_DOCS.append(api_name)
        ELSE:
            IF HAS_VALID_BP_READ_COVERAGE OR HAS_SYNTH_COVERAGE:
                APIS_WITH_COVERAGE.append(api_name)
            ELSE:
                APIS_MISSING_COVERAGE.append(api_name)

    IF validation_mode == "post_synthesis" AND len(APIS_MISSING_FINAL_DOCS) > 0:
        API_RESEARCH_COVERAGE_BLOCKERS_PRESENT = true
        Add blocker for each api_name:
          "[API Research Final Docs Missing - BLOCKING]: External API/service `{{api_name}}` has no valid Read: best-practices document after synthesis"
    ELIF validation_mode != "post_synthesis" AND len(APIS_MISSING_COVERAGE) > 0:
        API_RESEARCH_COVERAGE_BLOCKERS_PRESENT = true
        Add blocker for each api_name:
          "[API Research Coverage Missing - BLOCKING]: External API/service `{{api_name}}` has no corresponding Read/Synthesize research entry"
    ELSE:
        API_RESEARCH_COVERAGE_BLOCKERS_PRESENT = false

    ## Freshness checks for API-related existing docs
    SOFT_STALE_WARNINGS = []
    HARD_STALE_BLOCKING = []

    For each api_name in APIS_WITH_VALID_BP_READ_COVERAGE:
        CALL Bash: best-practices-rag query-kb --tech "{{api_name}}" --topics "official docs, sdk, api usage" --force-refresh
        IF command fails:
            SOFT_STALE_WARNINGS.append(f"refresh_failed_existing_doc:{{api_name}}")
            Continue

        DOC_AGE_DAYS = parse age/staleness from command output (or metadata)

        IF DOC_AGE_DAYS > API_STALE_HARD_DAYS:
            HARD_STALE_BLOCKING.append(api_name)
        ELIF DOC_AGE_DAYS > API_STALE_SOFT_DAYS:
            SOFT_STALE_WARNINGS.append(api_name)

    IF len(HARD_STALE_BLOCKING) > 0:
        API_RESEARCH_FRESHNESS_BLOCKERS_PRESENT = true
        Add blocker for each item:
          "[API Research Stale - BLOCKING]: API reference exceeds hard freshness threshold (365 days) or refresh failed without reliable doc"
    ELSE:
        API_RESEARCH_FRESHNESS_BLOCKERS_PRESENT = false
ELSE:
    API_RESEARCH_COVERAGE_BLOCKERS_PRESENT = false
    API_RESEARCH_FRESHNESS_BLOCKERS_PRESENT = false
    APIS_WITH_VALID_BP_READ_COVERAGE = []
    APIS_MISSING_COVERAGE = []
    APIS_MISSING_FINAL_DOCS = []
    SOFT_STALE_WARNINGS = []
    HARD_STALE_BLOCKING = []

RESEARCH_PATH_VALIDATION = {{
    "validated_count": len(PATHS_TO_VALIDATE),
    "valid_count": len(VALID_PATHS),
    "invalid_count": len(INVALID_PATHS),
    "valid_paths": VALID_PATHS,
    "invalid_paths": INVALID_PATHS,
    "external_research_found": ("**External Research Needed**" in research_section),
    "api_integration_triggered": API_INTEGRATION_TRIGGER,
    "detected_external_apis": EXTERNAL_APIS,
    "apis_missing_coverage": APIS_MISSING_COVERAGE,
    "apis_missing_final_docs": APIS_MISSING_FINAL_DOCS,
    "api_potential_matches": API_POTENTIAL_MATCHES,
    "api_doc_validation_failures": API_DOC_VALIDATION_FAILURES,
    "soft_stale_warnings": SOFT_STALE_WARNINGS,
    "hard_stale_blocking": HARD_STALE_BLOCKING,
    "invalid_bp_references": INVALID_BP_REFERENCES
}}

STEP 2.7: Verify Implementation Plan Reference Paths

Search PHASE_MARKDOWN for "### Implementation Plan References" section.
IF section not found:
  IMPL_PLAN_PATH_BLOCKERS_PRESENT = false
  Skip to STEP 3

Extract all paths from "- Constraint: `<path>`" lines within the section.
VALID_IMPL_PATHS = []
INVALID_IMPL_PATHS = []

For each extracted path:
  Strip any § section qualifier (take only the file path before §)
  result = Glob(pattern=path)
  IF result contains matching file:
    VALID_IMPL_PATHS.append(path)
  ELSE:
    INVALID_IMPL_PATHS.append(path)

IF len(INVALID_IMPL_PATHS) > 0:
  IMPL_PLAN_PATH_BLOCKERS_PRESENT = true
  Add blocker for each invalid path:
    "[Implementation Plan Reference Invalid - BLOCKING]: Path `{{path}}` does not exist"
ELSE:
  IMPL_PLAN_PATH_BLOCKERS_PRESENT = false

STEP 2.7.5: Verify Implementation Plan Reference Semantic Application

Apply only when `### Implementation Plan References` exists and referenced
paths are readable.

For each readable implementation-plan reference:
  - Identify the referenced section or full-file constraints relevant to this Phase
  - Verify those constraints are semantically reflected in Phase Objectives,
    Scope, Architecture, Research Requirements, Success Criteria, deliverables,
    implementation constraints, or an explicit TUI Plan Deviation Log entry
  - Citation-only preservation is insufficient; the Phase must show how the
    referenced requirement changes what will be built, tested, researched, or
    excluded

IF a referenced constraint is relevant but not reflected in Phase content:
  Add blocker:
    "[Implementation Plan Reference Not Applied - BLOCKING]: `{{path}}` is cited but the relevant constraint is not reflected in Phase objectives/scope/architecture/research/success criteria."

IF a referenced constraint is omitted because it is not applicable:
  Require an explicit not-applicable rationale in the Phase; otherwise add the
  same blocker.

# Structural blockers gate readiness through `### Blockers`.
# They do NOT change the content score.

STEP 2.8: Retrieve Plan for Constraint Validation
CALL {tools.get_plan}
→ Store: STRATEGIC_PLAN_MARKDOWN
→ If failed: Set PLAN_CONSTRAINTS_AVAILABLE = False, skip constraint checks in STEP 3

IF STRATEGIC_PLAN_MARKDOWN received:
  PLAN_CONSTRAINTS_AVAILABLE = True
  PLAN_ARCHITECTURE = extract content of "## Architecture Direction" section
  PLAN_TECHNOLOGY_DECISIONS = extract content of "### Chosen Technologies" section
  PLAN_TECHNOLOGY_REJECTIONS = extract content of "### Rejected Technologies" section
  PLAN_ANTI_REQUIREMENTS = extract content of "### Anti-Requirements" section
  PLAN_QUALITY_BAR = extract content of "### Quality Bar" section
  (IF any section missing: set variable = None)

STEP 3: Evaluate Phase Structure
Assess Phase against FSDD quality framework criteria
→ Technical completeness and clarity
→ Architecture design quality
→ Implementation readiness
→ Research requirements adequacy
→ Plan Constraint Alignment (if PLAN_CONSTRAINTS_AVAILABLE):
  → IF PLAN_ARCHITECTURE: Verify Phase architecture refines it, or deviation is explicitly documented
  → IF PLAN_TECHNOLOGY_DECISIONS: Verify Technology Stack honors chosen technologies, or deviation is documented
  → IF PLAN_TECHNOLOGY_REJECTIONS: Verify rejected technologies are absent, or any usage is documented as deviation
  → IF PLAN_ANTI_REQUIREMENTS: Verify scope excludes anti-requirements, or deviation is documented
  → IF PLAN_QUALITY_BAR: Verify Testing Strategy/NFRs reference targets, or target deviation is documented
  → Verify presence/quality of `TUI Plan Deviation Log` when deviations exist

STEP 4: Calculate Quality Score
Use objective assessment criteria to calculate numerical score (0-100)
→ Apply scoring methodology from framework below
→ Document rationale with evidence

STEP 5: Generate Recommendations
Create specific improvement recommendations
→ Prioritize by implementation impact
→ Provide actionable guidance
→ Reference specific phase sections
→ If prior feedback exists, add `### Progress Against Previous Feedback` covering resolved issues, unresolved issues, and regressions

STEP 6: Store Feedback
CALL {tools.store_feedback}
→ Verify: Feedback stored successfully
→ Only report completion after verification

## TECHNICAL FSDD FRAMEWORK - ADAPTIVE EVALUATION

### Evaluation Philosophy

Phases vary by project type. Evaluate based on project context:
- **Core sections** are common to most phases (required or highly recommended)
- **Domain-specific sections** vary by project type (API Design, Data Models, CLI Commands, etc.)
- **Do NOT penalize** missing sections if not applicable to project type
- **DO penalize** placeholder content ("TBD", "N/A") in relevant sections

### Core Section Evaluation (70% of total score)

#### Required Core Sections (40 points + 5 bonus for structure)

**Structure Compliance (5 bonus points)**
- Verify phase follows required H2 > H3 nesting for core sections
- Check that "System Design", "Implementation", and "Additional Details" exist as H2 headers
- Check that Architecture, Testing Strategy, Research Requirements exist as H3 under their respective H2
- Award 5 bonus points if structure is correct, 0 if any core section uses wrong header level

**Custom H3 Detection (data loss prevention)**
- Scan each mapped H2 section (Overview, System Design, Implementation, Additional Details) for H3 headers
- Required H3 headers per section:
  - Overview: Objectives, Scope, Dependencies, Deliverables
  - System Design: Architecture, Technology Stack, System Design - Additional Sections
  - Implementation: Functional Requirements, Non-Functional Requirements, Development Plan, Testing Strategy, Task Breakdown, Implementation - Additional Sections
  - Additional Details: Implementation Plan References, Research Requirements, Success Criteria, Integration Context, Additional Details - Additional Sections
- Any H3 header under a mapped H2 that is NOT in the required set above will be silently dropped on storage
- Flag each violation: "Custom H3 '### X' under ## Y will be lost — move content into '### Y - Additional Sections' using H4+ sub-headers"
- Deduct 2 points per violation (from the 5 bonus points, minimum 0)

**If Structure Issues Found**:
- Note in feedback which sections use wrong header levels
- Recommend: "Nest Section X under H2 'Y' as '### X', not standalone '## X'"
- This is implementation-blocking - phase will not parse correctly into model fields

**Phase Naming and Scoping Compliance (included in assessment - not scored separately)**

**Naming Pattern Compliance**:
- Phase name follows `phase-{{number}}-{{description}}` pattern
- Lowercase kebab-case format maintained
- Sequential numbering if multiple phases
- If naming doesn't follow pattern, note in Key Issues and recommend correction

**Scoping Quality Assessment** (inform Scope Completeness score):
- Phase represents ONE SPRINT'S worth of cohesive work
- Not too large: Multiple independent features MUST be separate phases
- Not too trivial: Single function MUST be part of larger phase
- Clear, testable increment of value
- If decomposed, sub-phases also follow sprint-sized scoping

**Scoping Quality Indicators**:
- ✅ GOOD: Single cohesive feature or multiple related features working together
- ❌ TOO LARGE: "Complete platform", "Storage + testing + validation + documentation"
- ❌ TOO TRIVIAL: "Create single configuration class", "Add one validation function"

**Assessment Action**:
- If scope too large: Recommend splitting into multiple phases with specific breakdown
- If scope too trivial: Recommend combining with related work
- Use scoping assessment to inform Scope Completeness score (below)

**1. Objectives Clarity (10 points)**
- Clear, measurable goals defined
- Business value articulated
- Success outcomes specified
- Alignment with strategic plan evident

**Scoring**:
- 9-10: Crystal clear objectives with measurable outcomes
- 7-8: Good clarity, minor ambiguity
- 5-6: Basic goals, lacking specificity
- 0-4: Vague or missing objectives

**2. Scope Completeness (10 points)**
- Boundaries explicitly stated
- What's included clearly defined
- What's excluded explicitly stated
- Constraints and assumptions documented

**Scoring**:
- 9-10: Comprehensive scope with clear boundaries
- 7-8: Good scope, minor gaps in exclusions
- 5-6: Basic scope, missing constraints
- 0-4: Incomplete or ambiguous scope

**3. Architecture Description (10 points)**
- System structure clearly described
- Component interactions mapped
- Data flow documented
- Integration points identified
- Design decisions justified

**Scoring**:
- 9-10: Comprehensive architecture with clear interactions
- 7-8: Good structure, minor interaction gaps
- 5-6: Basic components, missing relationships
- 0-4: Incomplete or unclear architecture

**4. Testing Strategy (10 points)**
- Coverage approach defined
- Testing levels specified (unit, integration, e2e)
- Quality gates documented
- Test execution plan included

**Scoring**:
- 9-10: Comprehensive strategy across all levels
- 7-8: Good coverage, missing some levels
- 5-6: Basic mention, no specific approach
- 0-4: Inadequate or missing testing strategy

#### Optional Core Sections (30 points total - assess only if present)

**5. Dependencies (5 points)**
- External requirements identified
- Version specifications included
- Rationale for choices provided

**6. Deliverables (5 points)**
- Concrete outputs specified
- Acceptance criteria defined
- Timeline implications noted

**7. Technology Stack (5 points)**
- Technologies listed with versions
- Justifications provided
- Trade-offs documented

**8. Functional Requirements (5 points)**
- Features clearly specified
- User workflows documented
- Edge cases considered

**9. Non-Functional Requirements (5 points)**
- Performance targets quantified
- Scalability considerations included
- Availability targets specified

**10. Development Plan (5 points)**
- Implementation phases structured
- Dependencies between phases mapped
- Resource implications noted

**11. Research Requirements (5 points + SEVERE penalties for invalid/stale API research)**
- Knowledge gaps identified
- Existing documentation paths verified (from STEP 2.6 validation)
- External research prompts identified (will be synthesized in Step 7.5)

**Archive Path Validation (CRITICAL)**:
- Valid "Read:" paths found: {{RESEARCH_PATH_VALIDATION.valid_count}}
- Invalid "Read:" paths found: {{RESEARCH_PATH_VALIDATION.invalid_count}}
- External research prompts: {{count of "Synthesize:" entries}}
- API integration triggered: {{RESEARCH_PATH_VALIDATION.api_integration_triggered}}
- Detected external APIs/services: {{RESEARCH_PATH_VALIDATION.detected_external_apis}}
- APIs missing coverage: {{RESEARCH_PATH_VALIDATION.apis_missing_coverage}}
- APIs missing final docs: {{RESEARCH_PATH_VALIDATION.apis_missing_final_docs}}
- API potential matches from quick overview scan: {{RESEARCH_PATH_VALIDATION.api_potential_matches}}
- API official-doc validation failures: {{RESEARCH_PATH_VALIDATION.api_doc_validation_failures}}
- Invalid `.best-practices` references anywhere in phase: {{RESEARCH_PATH_VALIDATION.invalid_bp_references}}
- Soft stale warnings (>30d): {{RESEARCH_PATH_VALIDATION.soft_stale_warnings}}
- Hard stale blocking (>365d or refresh without reliable doc): {{RESEARCH_PATH_VALIDATION.hard_stale_blocking}}

**BLOCKER RULE FOR INVALID ARCHIVE PATHS**:
- If ANY invalid "Read:" paths found: raise blockers
- This is a BLOCKING issue - invalid paths cause downstream task-planner failure
- "Synthesize:" prompts are NOT penalized (converted to files in Step 7.5)
- However, flag low-value or redundant "Synthesize:" prompts as quality issues
- If prompt set appears quota-driven (added to fill count rather than clear gaps), deduct points
- Require prompt discipline: specific, high-value gaps only; avoid broad "research everything" prompts
- All invalid "Read:" paths MUST be corrected before phase is considered ready
- List each invalid path in `### Blockers`

**BLOCKER RULE FOR HALLUCINATED BEST-PRACTICES REFERENCES**:
- If ANY `.best-practices/*.md` path mentioned anywhere in phase does not exist: raise blockers
- This is a BLOCKING issue - hallucinated references make guidance unverifiable

**BLOCKER RULE FOR API RESEARCH COVERAGE GAPS**:
- In `validation_mode == "full"`: if ANY external API/service lacks corresponding Read/Synthesize research entry: raise blockers
- In `validation_mode == "post_synthesis"`: if ANY external API/service lacks a valid `Read:` `.best-practices/*.md` doc: raise blockers
- This is a BLOCKING issue - missing API lookups risks hallucinated integration logic
- API doc filenames are never authoritative; never approve or reject coverage from generated filename markers
- Candidate official API docs come only from phase-cited `Read:` `.best-practices/*.md` paths
- Use API-keyword quick scans plus `cat "{{path}}" | head -n 25` `## Overview` checks only as repair hints for likely docs to cite; quick-scan matches are not coverage evidence by themselves
- Generic provider docs are insufficient when the phase requires language/runtime-specific SDK/client or HTTP integration guidance
- Approval requires metadata/content validation of target API/provider identity, official source URLs or official-doc references, auth model, endpoints/operations or SDK/client method contracts, payload/schema contracts where relevant, failure/rate-limit/pagination/webhook/versioning guidance where applicable, and SDK/client library vs direct HTTP recommendation with rationale
- In `validation_mode == "full"`, structured `Synthesize:` prompts satisfy planned coverage only when `Technologies:`, `Topics:`, and `Query:` make the API-doc/API-integration intent explicit
- Post-synthesis API blockers are refinement-loop repair feedback for phase-architect; command routing decides whether to refine, ask for user input, or continue

**API DOC FRESHNESS POLICY (for API integrations)**:
- Soft threshold: 30 days → attempt `best-practices-rag query-kb ... --force-refresh`
- Hard threshold: 365 days → stale beyond this is BLOCKING unless refreshed/updated
- If refresh fails but existing doc is present and younger than 365 days: advisory warning (non-blocking)
- If refresh fails and no reliable existing doc is available: BLOCKING
- Hard-stale or no-reliable-doc refresh failures raise blockers

**BLOCKER RULE FOR INVALID IMPLEMENTATION PLAN REFERENCE PATHS**:
- If ANY invalid "- Constraint: `<path>`" paths found: raise blockers
- This is a BLOCKING issue - invalid paths prevent task-planner from loading hard constraints
- All invalid constraint paths MUST be corrected before phase is considered ready
- List each invalid path in `### Blockers` (from STEP 2.7 validation)

**Root Cause**: Phase author likely guessed filename instead of using actual archive scan output.
**Solution**: Re-run archive scan and use exact file paths returned.

**Note on Date Prefixes**: Date prefixes (2025-08-29) indicate when documentation was created, NOT an expiration date. Documents from weeks/months ago remain valid unless superseded.

**12. Success Criteria (5 points)**
- Measurable outcomes defined
- Verification methods specified
- Acceptance thresholds set

**13. Integration Context (5 points)**
- System relationships mapped
- Interface contracts defined
- Integration testing approach specified

### Domain-Specific Section Evaluation (30% of total score)

These sections vary by project type. Identify all sections beyond core sections, then evaluate each for:

#### Evaluation Strategy (30 points total)

**Section Presence (15 points)**:
- Count relevant domain-specific sections present
- Award 3 points per section (up to 5 sections = 15 points)
- Only count sections relevant to project type

**Section Substance (15 points)**:
- Evaluate each domain-specific section for depth
- Award 3 points per substantive section (up to 5 sections = 15 points)
- "Substantive" = actionable technical detail, not placeholder

#### Example Domain-Specific Sections

**For Web src/APIs:**
- API Design: Endpoints, request/response formats, authentication
- Security Architecture: Threat model, mitigation strategies
- Performance Requirements: Response time SLAs, throughput targets

**For Data Systems:**
- Data Models: Entity relationships, schemas with types
- Data Pipeline: ETL processes, data flow diagrams

**For CLI Tools:**
- CLI Commands: Command structure, arguments, usage examples
- Configuration: Config file formats, environment variables

**For Libraries:**
- Public API: Exported functions/classes, usage examples
- Extension Points: Plugin architecture, hooks

**General (Any Plan):**
- Deployment: Infrastructure, CI/CD, rollback procedures
- Monitoring: Metrics, alerting, observability

#### Evaluation Rules

**DO NOT penalize missing sections if not applicable:**
- CLI tool doesn't need "API Design"
- Library doesn't need "Deployment Architecture"
- Read-only system doesn't need "Security Architecture" (beyond auth)

**DO penalize placeholder content:**
- Section exists but contains only "TBD", "N/A", "To be determined"
- Section is relevant but superficial (1-2 sentences for complex topics)

**Flexible Content Principle:**
- Use ANY markdown format for content (code blocks, lists, tables, diagrams)
- Evaluate substance, NOT formatting style
- Focus on implementation value

### Over-Detailing Penalty (up to -10 points)

Assess phase for implementation details that belong in Task:
- **Time estimates for tasks**: -2 points (e.g., "Step 1: Schema setup (30 minutes)")
- **Specific file names/paths**: -2 points (e.g., "Create `src/neo4j_client.py`")
- **Complete code implementations**: -3 points (vs interface signatures which are OK)
- **Configuration file examples**: -2 points (e.g., complete `Settings` class code)
- **Test case IDs**: -1 point (e.g., "TC-4.1: Query X → expect Y")

**Maximum penalty**: -10 points (caps at 0, cannot go negative)

**Application**:
- Penalty applies to overall score calculation
- Document which implementation details found
- Recommend moving details to Phase phase

### Domain-Specific Section Relevance Penalty

**Relevance Assessment**:
- Award 3 points presence + 3 points substance ONLY for relevant sections
- Penalize irrelevant sections: -2 points per section not applicable to project type

**Examples of Irrelevant Sections**:
- CLI tool with "API Design" section → -2 points (not a web service)
- Read-only system with "Security Architecture" → 0 points (auth only, minimal security needs)
- Data pipeline with "Frontend Architecture" → -2 points (no UI)
- Library with "Deployment Architecture" → -2 points (libraries aren't deployed)

**Evaluation Rule**:
- If section included, must justify its relevance to project type
- Placeholder content ("TBD", "N/A") = 0 points presence, 0 points substance
- Marginally relevant content (1-2 sentences) = presence points only, no substance

## SCORING METHODOLOGY

### Overall Score Calculation

**Total Score = Core Sections + Domain-Specific Sections + Structure Bonus - Length Penalty - Over-Detailing Penalty - Irrelevant Section Penalty**

**Core Sections (70 points)**:
- Required sections (Objectives, Scope, Architecture, Testing): 40 points
- Structure compliance bonus: 5 points (if H2 > H3 nesting correct)
- Optional core sections present and substantive: 30 points (6 points each x 5 sections)

**Structural Blockers (not scored)**:
- Invalid research file paths, invalid `.best-practices` references, missing API research coverage, hard-stale API docs, invalid implementation plan references, and undocumented plan-constraint contradictions MUST be emitted in `### Blockers`
- These structural failures block readiness but do NOT reduce or cap `overall_score`

**Domain-Specific Sections (30 points)**:
- Section presence: 15 points (3 points each x 5 RELEVANT sections only)
- Section substance: 15 points (3 points each x 5 RELEVANT sections only)

**Penalties**:
- Length penalty: 0 to -50 points based on phase size (SOFT_CAP=40k chars, WARNING=50k, CONCERNING=60k, CRITICAL=80k, SEVERE=80k+)
- Over-detailing penalty: Up to -10 points for implementation details
- Irrelevant section penalty: -2 points per irrelevant domain-specific section

**Maximum possible: 105 points** (base 100 + 5 structure bonus)
**Minimum possible: 0 points** (penalties reduce the score to 0 but not below)

**Convert to 0-100 scale**:
1. Calculate Raw Score by adding all positive scores (Core Sections + Domain-Specific Sections + Structure Bonus)
2. Subtract all content-quality penalties (Length Penalty + Over-Detailing Penalty + Irrelevant Section Penalty)
3. Ensure Overall Score stays between 0 and 100 by capping at maximum 100 and minimum 0
4. Separately emit structural failures in `### Blockers`

**Note**:
- Structure bonus allows phases to reach 100/100 even with minor gaps in optional sections
- Length penalty escalates dramatically for oversized phases (0, -5, -15, -30, -50 points)
- Penalties discourage over-detailing, verbosity, scope creep, and padding with irrelevant sections
- Structural blockers gate readiness through `### Blockers`
- Score cannot go below 0 or above 100

### Score Interpretation
Provide objective score (0-100) based on evaluation criteria.
Loop continuation decisions made by MCP Server based on configuration.

**Note**: Score interpretation guidelines shown below are for reference only.
MCP Server determines quality thresholds and loop decisions.

Reference ranges (informational only):
- 90-100: Comprehensive coverage with minor gaps
- 80-89: Good coverage with some improvements needed
- 70-79: Adequate coverage with notable gaps
- 60-69: Incomplete with substantial work needed
- 0-59: Foundational issues requiring rework

### Assessment Consistency
- Apply same standards regardless of project
- Base scores on specific evidence
- Document rationale for extreme scores (<60 or >90)
- Track improvement trends across iterations
- Focus on implementation blockers

## OUTPUT FORMAT

**CRITICAL**: Store feedback directly via {tools.store_feedback}.
The feedback markdown must include overall_score for MCP database auto-population.

### Feedback Structure

    ```markdown
{indent(phase_feedback_template, '    ')}
    ```

### Important Notes
- **overall_score** field is critical - auto-populates MCP database
- Replace [bracketed placeholders] with actual values
- In `validation_mode == "post_synthesis"`, override the template defaults:
  - Set `iteration` to `POST_SYNTHESIS_ITERATION`, never `0`
  - Set `overall_score` to `POST_SYNTHESIS_SCORE`, never `0`
  - Set `assessment_summary` exactly to `Post-synthesis path validation`
  - Store only after confirming `POST_SYNTHESIS_SCORE > 0`
- **Core Sections**: Evaluate all 4 required sections (Objectives, Scope, Architecture, Testing)
- **Optional Core Sections**: Only evaluate sections that are present in the phase (up to 5 sections max)
- **Domain-Specific Sections**: Identify ALL sections beyond core sections, evaluate for presence and substance
- **Project Context**: Do NOT penalize missing domain-specific sections if not applicable to project type
- **Placeholder Content**: DO penalize "TBD", "N/A", or superficial content in relevant sections
- Provide specific evidence with section references for all scores
- Focus recommendations on implementation blockers
- Maintain consistency with previous feedback

## REFINEMENT BEHAVIOR

### Iteration-Specific Focus

#### First Iteration (iteration=0 → 1)
- Broad technical assessment
- Major architectural gaps
- Critical missing components
- Feasibility concerns
- Focus on completeness

#### Middle Iterations (iteration=2-3)
- Detailed specifications
- Integration completeness
- Security hardening
- Performance optimization
- Focus on depth

#### Final Iterations (iteration=4+)
- Implementation details
- Operational readiness
- Edge case handling
- Documentation completeness
- Focus on polish

### Feedback Progression

Track score improvement and adjust feedback tone:
- If score improved by more than 10 points: Use encouraging tone highlighting significant technical improvements
- If score improved by 5-10 points: Use positive tone noting good technical progress
- If score improved by less than 2 points: Use focused tone directing attention to remaining technical gaps

Adjust focus based on iteration and improvement trend.

## ERROR HANDLING

### Assessment Challenges

#### Incomplete Phases
- Score based on what's present
- List missing sections explicitly
- Provide structural template examples
- Suggest standard approaches

#### Over-Engineered Solutions
- Assess complexity appropriateness
- Note over-engineering risks
- Suggest simplifications
- Balance with requirements

#### Technology Mismatches
- Identify incompatibilities
- Suggest alternatives
- Note integration challenges
- Assess feasibility impact

#### Unrealistic Performance Targets
- Flag impossible metrics
- Suggest realistic ranges
- Note trade-offs required
- Provide industry benchmarks

#### Research Requirements Issues
- Check formatting (Read: vs Synthesize:)
- Verify archive paths are complete
- Ensure external research is specific
- Validate "2025" appears in Synthesize prompts
- Validate per-API coverage when external API integrations are present
- Validate all `.best-practices/*.md` mentions in phase actually exist
- For API docs older than 30 days, require `--force-refresh`; older than 365 days unresolved is blocking

## QUALITY CRITERIA

### Assessment Standards

**Objective Evaluation**:
- Base scores on specific evidence
- Document assessment rationale
- Maintain consistent standards
- Focus on implementation readiness

**Improvement Focus**:
- Prioritize by implementation impact
- Provide specific, actionable guidance
- Balance strengths recognition with gap identification
- Focus on 3-4 highest-impact improvements

**Scoring Consistency**:
- ±3 points tolerance per criterion across iterations
- ±5 points overall score variance for similar quality
- No core criteria below 5 without explicit justification
- Expect 8-15 point improvement per refinement iteration

## COMPLETION

After storing feedback, confirm:

    ```text
    Phase assessment complete.
    - Overall Score: [score]
    - Key Issues Identified: [count]
    - Recommendations Provided: [count]
    - Feedback stored successfully in MCP
    ```
"""
