from src.platform.models import CodeCommandTools


def generate_code_command_template(tools: CodeCommandTools) -> str:
    ask_tool = tools.tui_adapter.ask_user_question_tool_name
    selection_prompt_instructions = (
        f'Use {ask_tool} tool to present options:'
        if ask_tool
        else (
            'Ask the user directly with a numbered options list and require a single explicit selection '
            'before continuing:'
        )
    )
    selection_response_source = f'{ask_tool} response' if ask_tool else 'the user response'
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase request]
description: Transform Phases into production-ready code through TDD-driven implementation
---

# respec-code Command: Implementation Orchestration

## Overview
Orchestrate the complete implementation workflow, transforming Phases into production-ready code through TDD-driven code development with comprehensive quality validation.

{tools.mcp_tools_reference}

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to MCP tools listed above.

When instructions say "CALL tool_name", you execute the tool:
  ✅ CORRECT: result = tool_name(param="value")
  ❌ WRONG: <tool_name><param>value</param>

DO NOT output XML. DO NOT describe what you would do. Execute the tool call.
═══════════════════════════════════════════════

## Workflow Steps

### 1. Parse User Inputs and Locate Phase File

Parse user inputs and locate the target phase without guessing at free-form boundaries:

#### Step 1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the project name]
RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]
```

#### Step 1.1.1: Initialize workflow variables

```text
PHASE_NAME_PARTIAL = [empty until RAW_PHASE_REQUEST is clarified]
OPTIONAL_CONTEXT = [empty until RAW_PHASE_REQUEST is clarified]
```

Fail closed on ambiguity:
- Treat RAW_PHASE_REQUEST as the only user-authored source of truth after PLAN_NAME.
- Do NOT assume RAW_PHASE_REQUEST has a clean boundary between the phase reference
  and additional implementation guidance.
- Ask the user a clarifying question or present options whenever multiple reasonable
  interpretations would change the selected phase, scope, implementation direction,
  validation criteria, or what to pass downstream as guidance.
- Do NOT begin phase lookup until the phase reference is sufficiently clear.

Once RAW_PHASE_REQUEST is sufficiently clear:
- PHASE_NAME_PARTIAL = [clarified phase selector derived from RAW_PHASE_REQUEST]
- OPTIONAL_CONTEXT = [remaining clarified implementation guidance, otherwise empty string]

If OPTIONAL_CONTEXT is present after clarification, preserve it for the full
code-implementation loop and pass it through to the coder, all reviewers, and
the deterministic MCP consolidation step.

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
  {selection_prompt_instructions}
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

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 1.3. Set PHASE_FILE_PATH. Continue to Step 1.4 immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  PHASE_FILE_PATH = [selected file path from {selection_response_source}]
```

#### Step 1.4: Extract canonical name from file path

```text
PHASE_NAME = [basename of PHASE_FILE_PATH without .md extension]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-2a")
- PHASE_NAME is the canonical name extracted from file path
- PLAN_NAME is used for all MCP storage operations
- All subsequent operations use PHASE_NAME (canonical)

### 2. Load and Store Existing Spec

Load phase from file system, store in MCP:

```text
{tools.sync_phase_instructions}
```

**Important**:
- PHASE_FILE_PATH is the full path from Step 1
- PHASE_NAME is the canonical name extracted from file path
- Phase is now in MCP storage for build workflow

**Note**: Build plans are not stored in external platforms - they only exist in MCP during the build workflow.

**Note on Step Numbering**: Step 3 was intentionally removed when research logic was moved to the phase workflow. Step numbering is preserved (1, 2, 4, 5...) for workflow compatibility.

### 4. Phase Validation
Coder agent will validate Phase exists when retrieving it:

```text
# Phase validation delegated to coder agent
# Coder retrieves Phase using loop_id and handles missing Phase error
# This follows the token optimization pattern - agents retrieve their own data
```

### 5. Retrieve Task from respec-task Command

Retrieve completed Task document from task workflow:

```text
TASK_MARKDOWN = {tools.get_task_document}

IF TASK_MARKDOWN not found:
  ERROR: "No Task found for Phase: {{PHASE_NAME}}"
  SUGGEST: "Run task workflow to create Task first"
  {tools.task_command_invocation}
  EXIT: Graceful failure with guidance

Display: "✓ Task retrieved - ready for implementation"
```

### 6. Check for Architectural Override Proposals

Use Task already retrieved in Step 5:

```text
# REUSE TASK_MARKDOWN from Step 5 (do not re-retrieve)

IF TASK_MARKDOWN contains "## Architectural Override Proposals" section:
  OVERRIDE_SECTION = [Extract section content]

  IF OVERRIDE_SECTION is not empty (has content beyond just header):
    Display to user:
    "⚠️ Task-planner has identified potential architecture improvements.

    Review override proposals in Task document.

    Choose action:
    1. Approve proposal → Re-run phase workflow to update architecture
    2. Reject proposal → Continue with current Phase as-is

    Task workflow paused until Phase updated.

    To approve:
    {tools.phase_command_invocation}
    To reject:
    {tools.code_command_invocation}

    EXIT: Workflow suspended pending user decision

IMMEDIATELY execute Step 6.5 (Mode Extraction) and Step 6.7 (Delivery Intent Resolution)
```

### 6.5 Extract Step Modes from Task

Parse Task document to determine which specialist reviewers to activate:

```text
# REUSE TASK_MARKDOWN from Step 5 (do not re-retrieve)

STEP_MODES = set()

For each "#### Step N:" section in TASK_MARKDOWN:
  Scan Step content for mode indicators:
  IF contains frontend keywords (UI, component, template, CSS, accessibility, HTMX, hx-, React, Vue, Svelte, Alpine.js, aria-, semantic HTML, form validation, responsive):
    STEP_MODES.add("frontend")
  IF contains API keywords (endpoint, REST, route, request, response, authentication, middleware):
    STEP_MODES.add("api")
  IF contains database keywords (schema, migration, model, query, index, SQL, ORM):
    STEP_MODES.add("database")
  IF contains infrastructure keywords (Docker, CI/CD, deployment, container, pipeline, environment):
    STEP_MODES.add("infrastructure")

Display: "✓ Detected step modes: {{STEP_MODES}}"
```

### 6.6 Resolve Active Reviewers

Determine which review agents to invoke based on detected modes:

```text
ACTIVE_REVIEWERS = ["automated-quality-checker", "spec-alignment-reviewer", "code-quality-reviewer"]

IF "frontend" in STEP_MODES:
  ACTIVE_REVIEWERS.append("frontend-reviewer")
IF "api" in STEP_MODES:
  ACTIVE_REVIEWERS.append("backend-api-reviewer")
IF "database" in STEP_MODES:
  ACTIVE_REVIEWERS.append("database-reviewer")
IF "infrastructure" in STEP_MODES:
  ACTIVE_REVIEWERS.append("infrastructure-reviewer")

Check for canonical coding standards config files:
STANDARDS_TOML_FILES = Glob(.respec-ai/config/standards/*.toml)
LANGUAGE_TOML_FILES = STANDARDS_TOML_FILES excluding universal.toml
IF LANGUAGE_TOML_FILES is not empty:
  ACTIVE_REVIEWERS.append("coding-standards-reviewer")

Read config files for coder agent:
STACK_CONFIG = Read(.respec-ai/config/stack.toml) if file exists, else ""
LANGUAGE_CONFIGS = For each file in LANGUAGE_TOML_FILES:
  Read(file) — concatenated content
GUIDE_FILES = Glob(.respec-ai/config/standards/guides/*.md)
STANDARDS_GUIDE = For each file in GUIDE_FILES:
  If filename stem matches a LANGUAGE_TOML_FILES stem: Read(file) — concatenated content
If no guide files match: STANDARDS_GUIDE = ""

WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:
  ## Workflow Guidance
  ### Guidance Summary
  [OPTIONAL_CONTEXT if present, otherwise "None"]
  ### Constraints
  - [preserved constraint from OPTIONAL_CONTEXT]
  - None
  ### Resume Context
  - [resume detail from OPTIONAL_CONTEXT]
  - None
  ### Settled Decisions
  - [clarified decision from OPTIONAL_CONTEXT]
  - None

PROJECT_CONFIG_CONTEXT_MARKDOWN = compose markdown:
  ## Project Config Context
  ### Stack Config TOML
  ```toml
  [STACK_CONFIG if present, otherwise "None"]
  ```
  ### Language Config TOMLs
  ```toml
  [LANGUAGE_CONFIGS if present, otherwise "None"]
  ```
  ### Standards Guide Markdown
  ```markdown
  [STANDARDS_GUIDE if present, otherwise "None"]
  ```

# Loop IDs in this command:
#   PLANNING_LOOP_ID  — task breakdown loop (from respec-task)
#   CODING_LOOP_ID    — Phase 1 functional loop (AQC + spec-alignment + domains)
#   STANDARDS_LOOP_ID — Phase 2 standards loop (coding-standards-reviewer only)
# Coder receives the loop ID matching its current phase.
# Each agent retrieves its own feedback using the loop_id it was given.

PHASE1_REVIEWERS = ACTIVE_REVIEWERS excluding "coding-standards-reviewer"
(coding-standards-reviewer runs in Phase 2 only)

Display: "✓ Active reviewers: {{ACTIVE_REVIEWERS}}"
Display: "✓ Phase 1 reviewers: {{PHASE1_REVIEWERS}}"
```

### 6.7 Resolve Delivery Intent Policy

Resolve execution mode deterministically before coding/review:

```text
# Required documents for policy resolution
PHASE_MARKDOWN = {tools.get_phase_document}
PLAN_MARKDOWN = mcp__respec-ai__get_document(doc_type="plan", key=PLAN_NAME, loop_id=None)

# Parse policy blocks (if present)
TASK_POLICY = extract from TASK_MARKDOWN:
  "### Acceptance Criteria > #### Execution Intent Policy"
PHASE_OVERRIDE = extract from PHASE_MARKDOWN:
  "### Success Criteria > #### Delivery Intent Override"
PLAN_DEFAULT = extract from PLAN_MARKDOWN:
  "## Quality Assurance > ### Delivery Intent Policy > Default Mode"
PLAN_TIE_BREAK = extract from PLAN_MARKDOWN:
  "## Quality Assurance > ### Delivery Intent Policy > Tie-Break Policy"

# Deterministic precedence
IF TASK_POLICY has valid Mode in {{MVP,hardening}}:
  RESOLVED_MODE = TASK_POLICY.mode
  RESOLVED_MODE_SOURCE = "task-policy"
ELIF PHASE_OVERRIDE has valid Mode in {{MVP,hardening}}:
  RESOLVED_MODE = PHASE_OVERRIDE.mode
  RESOLVED_MODE_SOURCE = "phase-override"
ELIF PLAN_DEFAULT has valid Mode in {{MVP,hardening}}:
  RESOLVED_MODE = PLAN_DEFAULT
  RESOLVED_MODE_SOURCE = "plan-default"
ELSE:
  RESOLVED_MODE = "MVP"
  RESOLVED_MODE_SOURCE = "default-MVP"

RESOLVED_TIE_BREAK = first non-empty of:
  TASK_POLICY.tie_break, PHASE_OVERRIDE.tie_break, PLAN_TIE_BREAK,
  "Prioritize core functional/spec delivery and defer non-P0 hardening risks."

AMBIGUOUS_MODE = conflicting explicit values across task/phase/plan sources

IF AMBIGUOUS_MODE:
  {selection_prompt_instructions}
    Header: "Resolve Mode"
    Question: "Delivery intent sources conflict. Select the mode for this coding loop."
    multiSelect: false
    Options:
      - MVP
      - hardening

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 6.7. Set RESOLVED_MODE. Continue to the resolved-mode display immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  RESOLVED_MODE = [user choice]
  RESOLVED_MODE_SOURCE = "user-selected-conflict-resolution"
```

Display:
- "✓ Resolved execution mode: {{RESOLVED_MODE}} (source: {{RESOLVED_MODE_SOURCE}})"
- "✓ Tie-break policy: {{RESOLVED_TIE_BREAK}}"

### 7. Coding Loop Initialization and Refinement
Set up and execute MCP-managed code quality refinement:

#### Step 7.1: Retrieve Task Loop ID from Task Workflow

Retrieve the task_loop_id that was created during respec-task:

```text
TASK_INFO = {tools.get_task_document}

TASK_LOOP_ID = [Extract loop_id from task metadata or use plan_name/phase_name to find active task loop]
```

#### Step 7.2: Initialize Coding Loop
```text
CODING_LOOP_ID = {tools.initialize_coding_loop}
```

#### Step 7.3: CRITICAL - Dual Loop ID Management

You now have TWO active loop IDs - DO NOT confuse them:

**task_loop_id = {{TASK_LOOP_ID}}**
- Purpose: Retrieve Task document (created during respec-task)
- Used by: coder (to get implementation plan), reviewers (to verify against Task/Phase)
- Storage: Task document linked to this loop

**coding_loop_id = {{CODING_LOOP_ID}}**
- Purpose: Store/retrieve code feedback
- Used by: coder (feedback retrieval), reviewers (structured result storage), MCP consolidation
- Storage: CriticFeedback for code quality

Pass BOTH IDs to coding agents. Never swap them.

#### Step 7.3.1: Persist Mode Snapshot to Loop Feedback

```text
MODE_SNAPSHOT_MARKDOWN = "## Execution Intent Snapshot\\n"
  + "- Mode: {{RESOLVED_MODE}}\\n"
  + "- Source: {{RESOLVED_MODE_SOURCE}}\\n"
  + "- Tie-Break Policy: {{RESOLVED_TIE_BREAK}}\\n"
  + "- Deferred Risk Register Source: Task Acceptance Criteria"

LOOP_ID = CODING_LOOP_ID
USER_FEEDBACK_MARKDOWN = MODE_SNAPSHOT_MARKDOWN
{tools.store_user_feedback}
```

#### Step 7.4: Phase 1 Iteration Loop (Coder → Reviews → Decision → Commit)

```text
Loop:
  REVIEW_ITERATION = REVIEW_ITERATION if defined else 1

  # A) Coder pass
  {tools.invoke_coder}
  Expected: Code implementation updated, task status synced, iteration handoff report returned

  # B) Phase 1 review team orchestration
  Launch ALL Phase 1 review agents in parallel.{tools.phase1_review_parallel_policy}
  Core reviewers always run; optional specialists based on PHASE1_REVIEWERS from Step 6.6.
  coding-standards-reviewer is excluded from Phase 1 and runs in Phase 2 only.

  Core reviewers (always active):
  {tools.invoke_quality_checker}
  {tools.invoke_spec_alignment}
  {tools.invoke_code_quality}

  Optional specialists:
  For each REVIEWER in PHASE1_REVIEWERS where REVIEWER is not core:
    {tools.invoke_dynamic_reviewer_pattern}

  # Consolidate deterministic reviewer results into CriticFeedback
  LOOP_ID = CODING_LOOP_ID
  ACTIVE_REVIEWERS = PHASE1_REVIEWERS
  {tools.consolidate_review_cycle}

  # C) MCP coding decision
  CODING_DECISION_RESPONSE = {tools.decide_coding_action}
  CODING_DECISION = CODING_DECISION_RESPONSE.status
  CODING_SCORE = CODING_DECISION_RESPONSE.current_score
  CODING_ITERATION = CODING_DECISION_RESPONSE.iteration
  Decision options: "COMPLETE", "REFINE", "USER_INPUT"

  # D) Phase 1 commit orchestration (command-owned, every pass)
  # Narrow exception: command reads latest feedback only for commit metadata synthesis.
  PHASE1_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=CODING_LOOP_ID, count=1)
  PHASE1_SCORE = [extract latest Overall Score from PHASE1_FEEDBACK]
  PHASE1_SUMMARY = [extract latest Assessment Summary from PHASE1_FEEDBACK]
  PHASE1_ACCOMPLISHED = [extract concise accomplished outcomes from PHASE1_FEEDBACK or coder handoff report]
  PHASE1_KEY_ISSUES = [extract top key issues from PHASE1_FEEDBACK]
  PHASE1_BLOCKERS_ACTIVE = PHASE1_FEEDBACK contains any of:
    "[Severity:P0]", "severity=P0", "**[P0]**", "[BLOCKING]"
  IF PHASE1_BLOCKERS_ACTIVE:
    PHASE1_REVIEW_STATUS = "blocked by active blockers"
  ELIF CODING_DECISION == "complete":
    PHASE1_REVIEW_STATUS = "ready for completion gate"
  ELSE:
    PHASE1_REVIEW_STATUS = "below completion threshold"

  # Loop commits are progress checkpoints only.
  # Completion commit is owned by Step 8.5 finalization gate.
  COMMIT_SUBJECT = "[WIP] {{PHASE_NAME}} [Phase 1 iter {{CODING_ITERATION}}]"

  COMMIT_MESSAGE_BLOCK = compose:
    {{COMMIT_SUBJECT}}

    Summary:
    {{PHASE1_SUMMARY}}

    Review Score: {{PHASE1_SCORE}}/100

    Accomplished:
    {{PHASE1_ACCOMPLISHED}}

    Remaining Issues/Blockers:
    {{PHASE1_KEY_ISSUES}}

    Phase: {{PHASE_NAME}}
    Loop: Phase 1 (coding_loop_id={{CODING_LOOP_ID}})
    Decision: {{CODING_DECISION}}
    Review Status: {{PHASE1_REVIEW_STATUS}}

    Source: MCP consolidated CriticFeedback

  COMMIT_MESSAGE_RULES:
  - Commit body MUST be exactly COMMIT_MESSAGE_BLOCK.
  - Do NOT append attribution trailers like Co-Authored-By, Signed-off-by, Generated-by, or similar.

  HAS_CHANGES = `git status --porcelain` has any output

  IF HAS_CHANGES:
    git add -A
    git commit --no-verify -F - <<'EOF'
    {{COMMIT_MESSAGE_BLOCK}}
    EOF
  ELSE:
    git commit --allow-empty --no-verify -F - <<'EOF'
    {{COMMIT_MESSAGE_BLOCK}}
    EOF

  LATEST_COMMIT_BODY = `git log -1 --pretty=%B`
  IF LATEST_COMMIT_BODY contains any prohibited attribution trailer:
    git commit --amend --no-verify -F - <<'EOF'
    {{COMMIT_MESSAGE_BLOCK}}
    EOF

  # E) Decision handling after commit
  IF CODING_DECISION == "refine":
    REVIEW_ITERATION = CODING_ITERATION + 1
    continue loop

  IF CODING_DECISION == "complete":
    exit loop to Step 8

  IF CODING_DECISION == "user_input":
    exit loop to Step 8
```

### 8. Coding Decision Handling

═══════════════════════════════════════════════
MANDATORY DECISION PROTOCOL
═══════════════════════════════════════════════
The MCP decision is FINAL. Execute the matching branch IMMEDIATELY.

"refine"     → Execute refinement. Do NOT ask, confirm, or present options to the user.
"user_input" → ONLY status that involves the user. Present feedback and wait for response.
"complete"   → Proceed to next step. Do NOT ask for confirmation.

VIOLATION: Asking the user whether to continue refining when status is "refine"
           is a workflow violation. The decision has already been made by the MCP server.
═══════════════════════════════════════════════

═══════════════════════════════════════════════
MANDATORY CODING LOOP LIMIT
═══════════════════════════════════════════════
Maximum coding loop iterations: 8

IF CODING_ITERATION >= 8 AND CODING_DECISION == "refine":
  Force "user_input" path — present feedback and wait for user guidance
  Display: "⚠ Coding loop reached iteration limit (8)"
═══════════════════════════════════════════════

```text
IF CODING_DECISION == "refine":
  Display: "🔵 [Phase 1 · Iteration {{CODING_ITERATION}}] ⟳ Rubric Score: {{CODING_SCORE}}/100 — {{PHASE1_REVIEW_STATUS}}; refining"
  Return to Step 7.4 (next loop pass runs coder → reviews → decision → commit).

ELIF CODING_DECISION == "complete":
  Display: "🔵 [Phase 1 · Complete] ✅ Rubric Score: {{CODING_SCORE}}/100 — ready for next phase (threshold met, no active blockers)"
  IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
    → IMMEDIATELY execute Step 7.5 (Standards Finalization Phase)
  ELSE:
    FINALIZATION_DECISION_SOURCE = "phase1-complete"
    → IMMEDIATELY execute Step 8.5 (Completion Gate)
  DO NOT ask user, DO NOT offer alternatives, DO NOT pause

ELIF CODING_DECISION == "user_input":
  LATEST_FEEDBACK = {tools.get_feedback}
  P0_ACTIVE = LATEST_FEEDBACK contains any of:
    "[Severity:P0]", "severity=P0", "**[P0]**", "[BLOCKING]"

  Display LATEST_FEEDBACK to user with:
  - Current rubric score and iteration
  - Key issues requiring attention
  - Recommended improvements

  IF P0_ACTIVE:
    {selection_prompt_instructions}
      1. Continue refine in current mode
      2. Switch mode and continue refine
  ELSE:
    {selection_prompt_instructions}
      1. Continue refine in current mode
      2. Switch mode and continue refine
      3. Finalize now with deferred-risk summary

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 8. Branch on the selected option. Continue with the matching action immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF user selects option 1:
    USER_FEEDBACK_MARKDOWN = "User selected continue refine in mode={{RESOLVED_MODE}}"
    LOOP_ID = CODING_LOOP_ID
    {tools.store_user_feedback}
    REVIEW_ITERATION = CODING_ITERATION + 1
    Return to Step 7.4

  IF user selects option 2:
    {selection_prompt_instructions}
      Header: "Switch Mode"
      Question: "Select new execution mode for this loop."
      Options: MVP, hardening
    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 8. Set RESOLVED_MODE. Continue with the loop-feedback update immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.
    RESOLVED_MODE = [user selection]
    RESOLVED_MODE_SOURCE = "user-switched-during-user_input"
    USER_FEEDBACK_MARKDOWN = "Execution Intent Snapshot updated: mode={{RESOLVED_MODE}} (switched by user)"
    LOOP_ID = CODING_LOOP_ID
    {tools.store_user_feedback}
    REVIEW_ITERATION = CODING_ITERATION + 1
    Return to Step 7.4

  IF user selects option 3:
    IF P0_ACTIVE:
      Display: "Cannot finalize while active P0 issues exist."
      Return to user_input options.
    ELSE:
      USER_FEEDBACK_MARKDOWN = "User finalized with deferred-risk summary in mode={{RESOLVED_MODE}}"
      LOOP_ID = CODING_LOOP_ID
      {tools.store_user_feedback}
      FINALIZATION_DECISION_SOURCE = "phase1-user-finalized"
      Proceed directly to Step 8.5 (Completion Gate)
```

### 7.5: Standards Finalization Phase

═══════════════════════════════════════════════
MANDATORY PHASE 2 ACTIVATION GATE
═══════════════════════════════════════════════
Run ONLY IF "coding-standards-reviewer" was in ACTIVE_REVIEWERS
(standards TOML files detected in Step 6.6).

IF no standards TOML files were found in .respec-ai/config/standards/:
  Skip Phase 2 entirely. Proceed directly to Step 8.5.
  Display: "ℹ️ No coding standards configured — skipping Phase 2"

Phase 2 has ZERO built-in rules. Without standards TOML files, there is
nothing to assess. Do NOT apply general coding standards.
═══════════════════════════════════════════════

#### Step 7.5.1: Initialize Standards Loop

```text
STANDARDS_LOOP_ID = {tools.initialize_standards_loop}
STANDARDS_REVIEW_ITERATION = 1

PHASE1_SCORE = [final Overall Score from CODING_LOOP_ID CriticFeedback]
Display:
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  PHASE 1 COMPLETE  ·  Functional Rubric Score: {{PHASE1_SCORE}}/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟣  PHASE 2 STARTING: Coding Standards
    Focus: naming · imports · type hints · docstrings
    Command orchestration owns commit lifecycle.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

#### Step 7.5.2: Standards Review Cycle

```text
Loop:
  REVIEW_ITERATION = STANDARDS_REVIEW_ITERATION

  {tools.invoke_coder_standards}

  {tools.invoke_coding_standards_reviewer}

  LOOP_ID = STANDARDS_LOOP_ID
  ACTIVE_REVIEWERS = ["coding-standards-reviewer"]
  {tools.consolidate_review_cycle}

  STANDARDS_DECISION_RESPONSE = {tools.decide_standards_action}
  STANDARDS_DECISION = STANDARDS_DECISION_RESPONSE.status
  STANDARDS_SCORE = STANDARDS_DECISION_RESPONSE.current_score
  STANDARDS_ITERATION = STANDARDS_DECISION_RESPONSE.iteration

  # Phase 2 feedback source (coding-standards reviewer CriticFeedback):
  STANDARDS_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=STANDARDS_LOOP_ID, count=1)
  STANDARDS_SUMMARY = [extract latest Assessment Summary from STANDARDS_FEEDBACK]
  STANDARDS_ACCOMPLISHED = [extract concise accomplished outcomes from STANDARDS_FEEDBACK or coder handoff report]
  STANDARDS_KEY_ISSUES = [extract top key issues from STANDARDS_FEEDBACK]
  STANDARDS_BLOCKERS_ACTIVE = STANDARDS_FEEDBACK contains any of:
    "[Severity:P0]", "severity=P0", "**[P0]**", "[BLOCKING]"
  IF STANDARDS_BLOCKERS_ACTIVE:
    STANDARDS_REVIEW_STATUS = "blocked by active blockers"
  ELIF STANDARDS_DECISION == "complete":
    STANDARDS_REVIEW_STATUS = "ready for completion gate"
  ELSE:
    STANDARDS_REVIEW_STATUS = "below completion threshold"

  # Loop commits are progress checkpoints only.
  # Completion commit is owned by Step 8.5 finalization gate.
  STANDARDS_COMMIT_SUBJECT = "[WIP] {{PHASE_NAME}} [Phase 2 iter {{STANDARDS_ITERATION}}]"

  STANDARDS_COMMIT_MESSAGE_BLOCK = compose:
    {{STANDARDS_COMMIT_SUBJECT}}

    Summary:
    {{STANDARDS_SUMMARY}}

    Review Score: {{STANDARDS_SCORE}}/100

    Accomplished:
    {{STANDARDS_ACCOMPLISHED}}

    Remaining Issues/Blockers:
    {{STANDARDS_KEY_ISSUES}}

    Phase: {{PHASE_NAME}}
    Loop: Phase 2 standards (loop_id={{STANDARDS_LOOP_ID}})
    Decision: {{STANDARDS_DECISION}}
    Review Status: {{STANDARDS_REVIEW_STATUS}}

    Source: coding-standards-reviewer CriticFeedback

  STANDARDS_COMMIT_MESSAGE_RULES:
  - Commit body MUST be exactly STANDARDS_COMMIT_MESSAGE_BLOCK.
  - Do NOT append attribution trailers like Co-Authored-By, Signed-off-by, Generated-by, or similar.

  HAS_CHANGES = `git status --porcelain` has any output
  IF HAS_CHANGES:
    git add -A
    git commit --no-verify -F - <<'EOF'
    {{STANDARDS_COMMIT_MESSAGE_BLOCK}}
    EOF
  ELSE:
    git commit --allow-empty --no-verify -F - <<'EOF'
    {{STANDARDS_COMMIT_MESSAGE_BLOCK}}
    EOF

  LATEST_COMMIT_BODY = `git log -1 --pretty=%B`
  IF LATEST_COMMIT_BODY contains any prohibited attribution trailer:
    git commit --amend --no-verify -F - <<'EOF'
    {{STANDARDS_COMMIT_MESSAGE_BLOCK}}
    EOF

  ═══════════════════════════════════════════════
  MANDATORY STANDARDS LOOP LIMIT
  ═══════════════════════════════════════════════
  Maximum standards loop iterations: 5

  IF STANDARDS_ITERATION >= 5 AND STANDARDS_DECISION == "refine":
    Force "user_input" path — present feedback and wait for user guidance
    Display: "⚠ Standards loop reached iteration limit (5)"
  ═══════════════════════════════════════════════

  IF STANDARDS_DECISION == "complete":
    Display: "🟣 [Phase 2 · Complete] ✅ Rubric Score: {{STANDARDS_SCORE}}/100 — ready for completion gate (threshold met, no active blockers)"
    exit loop

  IF STANDARDS_DECISION == "refine":
    STANDARDS_REVIEW_ITERATION = STANDARDS_ITERATION + 1
    Display: "🟣 [Phase 2 · Iteration {{STANDARDS_ITERATION}}] ⟳ Rubric Score: {{STANDARDS_SCORE}}/100 — {{STANDARDS_REVIEW_STATUS}}; refining standards"
    continue loop

  IF STANDARDS_DECISION == "user_input":
    STANDARDS_FEEDBACK = {tools.get_standards_feedback}
    Display stagnation info with: phase 1 score, phase 2 current score, iterations, key issues

    {selection_prompt_instructions}
      1. Continue Phase 2 with more iterations
      2. Finalize current standards state now

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 7.5. Branch on the selected option. Continue with the matching standards action immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

    Store user choice and branch accordingly:
    - Option 1: STANDARDS_REVIEW_ITERATION = STANDARDS_ITERATION + 1
                continue loop
    - Option 2: FINALIZATION_DECISION_SOURCE = "phase2-user-finalized"
                EXIT Phase 2 loop → Step 8.5
```

#### Step 7.5.3: Exit to Completion Gate

```text
IF STANDARDS_DECISION == "complete":
  FINALIZATION_DECISION_SOURCE = "phase2-complete"
  Proceed to Step 8.5 (Completion Gate)
```

### 8.5 Completion Gate (Mandatory)

```text
# Ensure source label exists for completion metadata.
IF FINALIZATION_DECISION_SOURCE is empty:
  FINALIZATION_DECISION_SOURCE = "loop-complete"

COMPLETION_GATE_STATUS = "passed"
COMPLETION_GATE_SUMMARY = "pre-commit run -a passed."

# Enforce repository hooks exactly once before final completion commit.
PRECOMMIT_EXIT_CODE = run: pre-commit run -a

IF PRECOMMIT_EXIT_CODE != 0:
  Display: "❌ Completion gate failed: pre-commit hooks reported issues."
  Display: "Finalization is non-compliant until hooks pass."
  Display: "Classify the failure from the hook transcript before branching."

  COMPLETION_GATE_FAILURE_KIND = classify from hook transcript as exactly one of:
    - "actionable_repo_issue"
    - "external_blocker"

  Classification rules:
  - Use "actionable_repo_issue" when the failure is fixable by repository changes the workflow owns:
    formatting/import rewrites, lint failures, type-check failures, test failures,
    terraform fmt changes, generated-file drift, missing repo configuration, or any hook
    output that points to code/config/content changes inside the workspace.
  - Use "external_blocker" only when the failure is outside repo control and cannot be
    resolved by another refinement pass:
    missing API keys/credentials, unavailable external services, network outages, rate
    limits, or missing system prerequisites the workflow does not provision.

  COMPLETION_GATE_FAILURE_SUMMARY = [one concise sentence quoting the concrete blocker]

  IF COMPLETION_GATE_FAILURE_KIND == "actionable_repo_issue":
    USER_FEEDBACK_MARKDOWN = "Completion gate failed; automatic refine due to actionable hook failure in mode={{RESOLVED_MODE}}. Blocker: {{COMPLETION_GATE_FAILURE_SUMMARY}}"
    LOOP_ID = (
      STANDARDS_LOOP_ID if "coding-standards-reviewer" in ACTIVE_REVIEWERS
      else CODING_LOOP_ID
    )
    {tools.store_user_feedback}
    Display: "↩ Returning to refinement automatically: {{COMPLETION_GATE_FAILURE_SUMMARY}}"
    IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
      Return to Step 7.5.2
    ELSE:
      Return to Step 7.4

  IF COMPLETION_GATE_FAILURE_KIND == "external_blocker":
    COMPLETION_GATE_STATUS = "deferred-external-blocker"
    COMPLETION_GATE_SUMMARY = {{COMPLETION_GATE_FAILURE_SUMMARY}}
    FINALIZATION_DECISION_SOURCE = "{{FINALIZATION_DECISION_SOURCE}}+external-gate-deferred"
    Display: "⚠ Proceeding to final completion commit with deferred external blocker: {{COMPLETION_GATE_FAILURE_SUMMARY}}"

# pre-commit sometimes rewrites tracked files or adds cleanup-only changes.
# Treat any resulting diffs as part of the final workflow output.
# Do not question or call out these changes; stage the full tree and commit it.
# pre-commit succeeded; compose dedicated completion commit.
IF "coding-standards-reviewer" in ACTIVE_REVIEWERS:
  FINAL_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=STANDARDS_LOOP_ID, count=1)
  FINAL_LOOP_LABEL = "Phase 2 standards"
  FINAL_LOOP_ID = STANDARDS_LOOP_ID
  FINAL_SOURCE = "coding-standards-reviewer CriticFeedback"
ELSE:
  FINAL_FEEDBACK = mcp__respec-ai__get_feedback(loop_id=CODING_LOOP_ID, count=1)
  FINAL_LOOP_LABEL = "Phase 1"
  FINAL_LOOP_ID = CODING_LOOP_ID
  FINAL_SOURCE = "MCP consolidated CriticFeedback"

FINAL_SCORE = [extract latest Overall Score from FINAL_FEEDBACK]
FINAL_SUMMARY = [extract latest Assessment Summary from FINAL_FEEDBACK]
FINAL_ACCOMPLISHED = [extract concise accomplished outcomes from FINAL_FEEDBACK or coder handoff report]
FINAL_KEY_ISSUES = [extract top key issues from FINAL_FEEDBACK]

FINAL_COMMIT_MESSAGE_BLOCK = compose:
  feat: complete {{PHASE_NAME}}

  Summary:
  {{FINAL_SUMMARY}}

  Review Score: {{FINAL_SCORE}}/100

  Accomplished:
  {{FINAL_ACCOMPLISHED}}

  Remaining Issues/Blockers:
  {{FINAL_KEY_ISSUES}}

  Phase: {{PHASE_NAME}}
  Finalization Source: {{FINALIZATION_DECISION_SOURCE}}
  Final Loop: {{FINAL_LOOP_LABEL}} (loop_id={{FINAL_LOOP_ID}})
  Completion Gate: {{COMPLETION_GATE_STATUS}}
  Completion Gate Summary: {{COMPLETION_GATE_SUMMARY}}

  Source: {{FINAL_SOURCE}}

FINAL_COMMIT_MESSAGE_RULES:
- Commit body MUST be exactly FINAL_COMMIT_MESSAGE_BLOCK.
- Do NOT append attribution trailers like Co-Authored-By, Signed-off-by, Generated-by, or similar.

git add -A
git commit --allow-empty --no-verify -F - <<'EOF'
{{FINAL_COMMIT_MESSAGE_BLOCK}}
EOF

LATEST_COMMIT_BODY = `git log -1 --pretty=%B`
IF LATEST_COMMIT_BODY contains any prohibited attribution trailer:
  git commit --amend --no-verify -F - <<'EOF'
  {{FINAL_COMMIT_MESSAGE_BLOCK}}
  EOF

Proceed directly to Step 9 (Integration & Documentation)
```

### 9. Integration & Documentation
Complete implementation workflow and update Phase:

#### Generate Implementation Summary
```text
Retrieve final state:
- Phase: {tools.get_task_document})
- Final Feedback: {tools.get_feedback})

Generate IMPLEMENTATION_SUMMARY including:
- Task Plan Quality Score: {{PLAN_QUALITY_SCORE}}%
- Code Quality Score: {{CODE_QUALITY_SCORE}}%
- Test Results: {{TEST_RESULTS from CriticFeedback}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Files Modified: {{FILE_COUNT}}
- Commit Summary: {{GIT_LOG_SUMMARY}}
```

#### Update Phase
```text
Update Phase status and implementation details using {tools.store_phase_document}:

Status: "IMPLEMENTED"
Implementation Summary: {{IMPLEMENTATION_SUMMARY}}
Phase Quality: {{PLAN_QUALITY_SCORE}}%
Code Quality: {{CODE_QUALITY_SCORE}}%
Test Coverage: {{COVERAGE_PERCENTAGE}}%
Implementation Date: {{CURRENT_DATE}}
```

#### Report Completion
```text
Present final summary:
"✓ Implementation complete for {{PHASE_NAME}}

Task Planning:
- Quality Score: {{PLAN_QUALITY_SCORE}}%
- Iterations: {{TASK_ITERATION_COUNT}}

Code Implementation:
- Quality Score: {{CODE_QUALITY_SCORE}}%
- Iterations: {{CODING_ITERATION_COUNT}}
- Tests Passing: {{TESTS_PASSING}}/{{TOTAL_TESTS}}
- Coverage: {{COVERAGE_PERCENTAGE}}%
- Type Checker: {{TYPE_CHECKER_STATUS}}
- Linter: {{LINTER_STATUS}}

Implementation artifacts:
- Phase: Available via task_loop_id={{TASK_LOOP_ID}}
- Code Review: Available via coding_loop_id={{CODING_LOOP_ID}}
- Commits: {{COMMIT_COUNT}} commits with test results
- Completion Gate: {{COMPLETION_GATE_STATUS}} — {{COMPLETION_GATE_SUMMARY}}
- Phase Status: Updated via {tools.store_phase_document}

Ready for deployment."
```

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

**Build agents:** Use normalized phase names when retrieving Phases via MCP.

## Quality Gates

### Quality Assessment
- **Phase Evaluation**: Assessed by task-critic agent
- **Code Quality Evaluation**: Assessed by review team (automated-quality-checker, spec-alignment-reviewer, code-quality-reviewer, optional specialists) with deterministic MCP consolidation.
- **Loop Decisions**: Made by MCP Server based on configuration
- **Thresholds and Limits**: Managed by MCP Server

### Assessment Criteria

**Phase Assessment Criteria**:
1. Plan Completeness: All sections populated with substantive content
2. Phase Alignment: Matches objectives, scope, architecture
3. Test Strategy Clarity: TDD approach and test organization defined
4. Implementation Sequence Logic: Dependencies respected, phases logical
5. Technology Appropriateness: Stack suitable for requirements

**Code Quality Assessment Criteria**:
1. Tests Passing: All tests execute successfully
2. Type Checking Clean: Type checker reports zero errors
3. Linting Clean: Linter reports zero issues
4. Test Coverage: Adequate coverage of critical paths
5. Phase Alignment: File structure and features match plan
6. Phase Requirements: All objectives implemented

Note: Loop decisions determined by MCP Server based on scoring and configuration

## Error Handling

### Graceful Degradation Patterns

#### Phase Not Available
```text
Display: "No Phase found: [PHASE_NAME]"
Suggest: "Use phase workflow to create Phase"
{tools.phase_command_invocation}
Exit gracefully with guidance
```

#### Coding Loop Failures
```text
IF coder fails:
  Preserve git commits for rollback
  Report failure with TodoList state
  Provide diagnostic information
  Suggest manual intervention

IF review team fails:
  Run static analysis manually (Bash: test runner, type checker, linter from Phase tech stack)
  Report test results without quality score
  Continue with manual quality assessment
  Note automated review unavailable
```

#### MCP Loop Failures
```text
IF loop initialization fails:
  Continue with single-pass workflow
  Skip refinement cycles
  Note quality loops unavailable
  Suggest manual review at each phase
```

## Coordination Pattern

The command maintains orchestration focus by:
- **Validating Phase completion** before proceeding
- **Coordinating agent invocations** without defining their behavior
- **Maintaining dual loop IDs** (task_loop_id + coding_loop_id)
- **Handling MCP Server responses** without evaluating quality scores
- **Managing user feedback** during stagnation scenarios
- **Providing error recovery** without detailed implementation guidance

All specialized work delegated to appropriate agents:
- **coder**: TDD code implementation (MCP access + platform tools)
- **automated-quality-checker**: Static analysis (tests, types, lint, coverage)
- **spec-alignment-reviewer**: Task/Phase/Plan alignment verification
- **code-quality-reviewer**: Structural quality, correctness patterns, research compliance, design assessment
- **specialist reviewers**: Domain-specific review (frontend, API, database, infrastructure)
- **MCP consolidate_review_cycle**: Merges reviewer results into single CriticFeedback
- **MCP Server**: Decision logic, threshold management, state storage

## Workflow Enhancements

### Dual Loop Architecture
- Separate task loop (from respec-task) and coding loop (code refinement)
- task_loop_id used to retrieve Task document created by task workflow
- coding_loop_id used for code feedback storage/retrieval
- Coding agents receive both IDs and use appropriately

### Coding Standards Integration
- coder reads platform-specific coding standards on initialization
- User-customizable coding standards applied to all generated code
- Fallback to Phase Code Standards if not available

### TDD Enforcement
- Strict test-first discipline enforced by coder agent
- Tests must fail before implementation proceeds
- Tests must pass before considering feature complete
- Commit after each iteration for rollback capability

### User Feedback During Stagnation
- User input requested when quality plateaus (<5 points over 2 iterations)
- User feedback stored via {tools.store_user_feedback}
- Agents retrieve all feedback (critic + user) via {tools.get_feedback}
- User feedback takes priority over critic suggestions when conflicts exist

Ready for production deployment with validated quality scores and comprehensive test coverage.
"""
