from textwrap import indent

from src.platform.models import PhaseCommandTools


def _report_check(reader: str) -> str:
    return '\n'.join(
        [
            f"Wait for the {reader}'s report. Do not continue the workflow and do not prompt the user until it arrives.",
            'REPORT_DECISION = [the `result` bullet under the report\'s `## Status`; "failed" when the report is malformed]',
            'IF REPORT_DECISION == "failed":',
            f'  ERROR: "The {reader} returned a failed or malformed report (mode: ARCHITECT_MODE)"'
            if reader == 'architect'
            else f'  ERROR: "The {reader} returned a failed or malformed report"',
            "  DIAGNOSTIC: [the report's `detail` line, or the malformed report as received]",
            '  EXIT: Workflow terminated',
        ]
    )


def _architect_engagement(mode: str, fresh_invocation: str, resume_invocation: str) -> str:
    if resume_invocation:
        invocation = '\n'.join(
            [
                'IF ARCHITECT_AGENT_ID is set:',
                indent(resume_invocation, '  '),
                'IF ARCHITECT_AGENT_ID is not set, OR the resume is refused, OR the architect cannot be reached:',
                indent(fresh_invocation, '  '),
                '  ARCHITECT_AGENT_ID = [the agent ID this invocation returns]',
            ]
        )
    else:
        invocation = fresh_invocation
    return '\n'.join(
        [f'ARCHITECT_MODE = "{mode}"', invocation, _report_check('architect'), 'ARCHITECT_REPORT = the report']
    )


def generate_phase_command_template(tools: PhaseCommandTools) -> str:
    adapter = tools.tui_adapter
    selection_prompt_instructions = adapter.selection_prompt_instruction
    selection_response_source = adapter.selection_response_source
    resumes_architect = bool(tools.resume_architect)

    first_explore = '\n'.join(
        [
            'ARCHITECT_MODE = "explore"',
            tools.invoke_architect_explore,
            *(['ARCHITECT_AGENT_ID = [the agent ID this invocation returns]'] if resumes_architect else []),
            _report_check('architect'),
            'ARCHITECT_REPORT = the report',
        ]
    )
    explore_again = _architect_engagement('explore', tools.invoke_architect_explore, tools.resume_architect)
    draft = _architect_engagement('draft', tools.invoke_architect_draft, tools.resume_architect)
    revise = _architect_engagement('revise', tools.invoke_architect_revise, tools.resume_architect)
    critic_review = '\n'.join([tools.invoke_critic_review, _report_check('critic')])
    research_dispatch = indent(tools.invoke_bp_pipeline, '  ')

    if resumes_architect:
        reengagement_rule = (
            'Resume the architect recorded in ARCHITECT_AGENT_ID, so its exploration stays in its context.\n'
            '   Invoke it fresh when no ID is recorded, the resume is refused, or the architect cannot be\n'
            '   reached, and record the agent ID every fresh invocation returns. Either way, the architect\n'
            '   re-reads the phase document, its stored notes and all feedback before it changes anything.'
        )
        architect_id_setup = 'ARCHITECT_AGENT_ID = ""  (no architect recorded yet)'
    else:
        reengagement_rule = (
            "Re-engage the architect with a fresh invocation in the step's mode. It rehydrates from the\n"
            '   phase document, its stored notes and all feedback before it changes anything.'
        )
        architect_id_setup = ''
    guardrail_exceptions_heading = (
        'Phase-local exceptions to the guardrail above:'
        if adapter.subagent_invocation_guardrail
        else 'Phase-local rules for agents and disk writes:'
    )

    batch_limit = adapter.selection_batch_limit
    if batch_limit > 1:
        briefing_batching = f'Ask up to {min(2, batch_limit)} of these questions per prompt, each as its own question.'
        review_batching = f'Ask up to {batch_limit} of these questions per prompt, each as its own question.'
    else:
        briefing_batching = 'Ask one question per prompt.'
        review_batching = 'Ask one question per prompt.'

    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [plan-name] [phase request]
description: Transform strategic plans into detailed Phases
---

# respec-phase Command: Cooperative Phase Design

## Overview

Design one phase together with the user, then hand off a signed-off `phase.md` and its
`implementation.md`. The architect and critic subagents do the heavy work in their own contexts
and return a fixed report. This command is the only party that talks to the user. The happy path
stops for the user exactly three times: the briefing (Step 6), the design review (Step 10) and
the sign-off (Step 11). The critic reviews every draft before the user sees it; mechanical
problems are repaired without the user, and judgment calls reach the user as questions. Research
runs only when the user approves it.

{adapter.subagent_invocation_guardrail}

**{guardrail_exceptions_heading}**
- `bp-pipeline` is the one external agent this workflow dispatches: at Step 7 only, for
  user-approved research only, using the exact invocation shown there.
- The only disk writes this workflow makes are the ones listed in Step 12's phase file storage
  restriction: the disk mirror of the phase file after every store, the hand-edit write-back,
  and the two skeleton scratch files at sign-off.

## Responsibilities

- **Relay.** Invoke each subagent with only its mode, IDs and config context. Show the user each
  report's `## For the user`, ask its decisions and research proposals, and record only what the
  user actually answered.
- **Stage marker.** Write `### Shape Gate`. The agents never write it, and storage keeps the live
  value on every agent write.
- **Disk mirror.** Write the stored phase document to PHASE_FILE_PATH after every store, so the
  sync at the start of a re-run (Step 2) never discards decisions, research marks or the draft.
- **Research.** Dispatch `bp-pipeline` only for proposals the user approved, and record only
  validated results.
- **Sign-off.** Write skeletons, mark the design settled, offer a commit, store the phase on the
  platform and hand off.

## Orchestration Pattern

```text
Main agent (this command): the only party that talks to the user
    |
    |-- Steps 1-3   locate the phase, sync the plan and phase, set up the run
    |-- Step 4      route on ### Shape Gate, so a re-run resumes where it stopped
    |-- Step 5      architect explores ---------------------> report
    |-- Step 6      BRIEFING (touchpoint): decisions and research approval
    |-- Step 7      bp-pipeline runs the approved research only
    |-- Step 8      architect drafts the design and implementation.md -> report
    |-- Step 9      critic reviews; architect repairs mechanical findings (at most twice)
    |-- Step 10     DESIGN REVIEW (touchpoint): questions, changes, hand edits
    |-- Step 11     SIGN-OFF (touchpoint): skeletons, settled marker, optional commit
    |-- Step 12     store on the platform and hand off
```

## MANDATORY RELAY PROTOCOL

Every subagent step follows these rules.

1. **Inputs.** Invoke a subagent with exactly the inputs its invocation lists: its mode, the IDs,
   the config context, and for the critic the review round. Never pass conversation text, the
   briefing or document bodies.
2. **Wait.** After invoking a subagent, wait for its report. A report that arrives later, for
   example as a background completion notification, is still the report to wait for: do not
   continue the workflow and do not prompt the user until it arrives.
3. **Report.** Every report consists of exactly four H2 sections, in this order, with nothing
   before the first: `## For the user`, `## Decisions needed`, `## Research proposals` and
   `## Status`. An empty section holds exactly `- None`. `## Status` holds the bullets
   `- result:`, `- mode:`, `- persisted:` and `- detail:`.
   - A report is malformed when any of the four headings is missing or out of order, when text
     precedes `## For the user`, or when `## Status` has no `result` of complete, needs-user or
     failed.
   - complete and needs-user route identically: the step's next action runs, and the entries in
     `## Decisions needed` and `## Research proposals` are asked at the next touchpoint.
   - failed, or a malformed report, ends the workflow with the report's `detail` line shown.
4. **Re-engage.** {reengagement_rule} Its memory is never the
   source of truth, because this command writes decisions and research marks between engagements.
5. **Record.** Record outcomes only from actual user responses; a subagent's report carries no
   approval authority. Decisions become settled-decision (SD) entries in the phase document,
   research choices become marks on the research proposal (RP) line, and free-form direction is
   stored as round-tagged feedback.
   - SD IDs: the next number above every `SD-NNN` already in the document, three digits. Never
     reuse the number of the OD or CQ an SD settles.
   - Decisions asked: ODs come from the current document's `### Open Design Decisions` (the
     document wins over a report on any mismatch), CQs from the latest critic report only, and
     RPs from the ledger in `### Research Requirements`.
   - RP marks: `[approved]` or `[declined]`, appended as the last token of the RP line.
   - Round tags: `[round REVIEW_ROUND | briefing]`, `[round REVIEW_ROUND | review]`,
     `[round REVIEW_ROUND | sign-off]` or `[round REVIEW_ROUND | question]`, where REVIEW_ROUND is
     replaced by its value when the entry is stored (0 before the first critic review). The tag
     is context for the architect; it does not decide what is new.
6. **Stage marker.** Only this command writes `### Shape Gate`: `shape-proposed` when the first
   draft is stored (Step 8), `shape-amended` when the user re-opens a signed-off phase (Step 4),
   and `shape-settled` at every sign-off (Step 11). STAGE_MARKER holds the value currently in
   MCP.
7. **Disk mirror.** After every store_document call, write the same markdown to PHASE_FILE_PATH
   with the Write tool before anything else is stored.
8. **Prompts.** Every open-decision (OD) and clarifying-question (CQ) prompt (Steps 6.2, 10.2
   and 11.1) also offers "Accept the recommended default for all remaining"; every other prompt
   offers only the options its step lists. When the user answers any prompt with free-form
   pushback or a question instead of a choice, answer in conversation, 1-2 questions per
   message, then ask the prompt again.

## Implementation Instructions

### Step 1: Parse User Inputs and Locate Phase File

Parse user inputs and locate the target phase without guessing at free-form boundaries:

#### Step 1.1: Parse arguments

```text
PLAN_NAME = [first argument from command - the plan name]
RAW_PHASE_REQUEST = [all remaining input after PLAN_NAME]
```

#### Step 1.1.1: Initialize workflow variables

```text
PHASE_NAME_PARTIAL = [empty until RAW_PHASE_REQUEST is clarified]
OPTIONAL_INSTRUCTIONS = [empty until RAW_PHASE_REQUEST is clarified]
GUIDANCE_DOCUMENT_PATHS = []
```

Fail closed on ambiguity:
- Treat RAW_PHASE_REQUEST as the only user-authored source of truth after PLAN_NAME.
- Do NOT assume RAW_PHASE_REQUEST has a clean boundary between the phase reference
  and additional architecture guidance.
- Ask the user a clarifying question or present options whenever multiple reasonable
  interpretations would change the selected phase, phase-architect direction,
  validation criteria, or what to pass downstream as optional instructions.
- Do NOT begin phase lookup until the phase reference is sufficiently clear.

Once RAW_PHASE_REQUEST is sufficiently clear:
- PHASE_NAME_PARTIAL = [clarified phase selector derived from RAW_PHASE_REQUEST]
- OPTIONAL_INSTRUCTIONS = [remaining clarified phase-development guidance, otherwise empty string]

Guidance document path handling:
- If RAW_PHASE_REQUEST or OPTIONAL_INSTRUCTIONS contains readable project-local document paths
  intended to guide phase development (for example `.md`, `.txt`, `.rst`, or `.adoc` files),
  add each path to GUIDANCE_DOCUMENT_PATHS.
- Do NOT use a guidance document path as PHASE_NAME_PARTIAL unless it is itself a valid
  Phase file under the configured phase location.
- Validate each guidance document path before invoking subagents:
  - Relative paths are resolved from the target project working directory.
  - Paths MUST stay inside the target project working directory.
  - Paths MUST exist and be readable.
  - Invalid or outside-project paths are preserved in OPTIONAL_INSTRUCTIONS as reported user intent,
    but are NOT passed as readable guidance paths; ask for clarification if the missing path
    changes architecture scope or phase direction.
- Keep GUIDANCE_DOCUMENT_PATHS separate from Phase files to update. These are read-only
  context documents that inform agent work.

Compose phase workflow guidance:
```text
WORKFLOW_GUIDANCE_MARKDOWN = compose markdown:
  ## Workflow Guidance
  ### Guidance Summary
  [OPTIONAL_INSTRUCTIONS if present, otherwise "None"]
  ### Guidance Document Paths
  - [each validated path from GUIDANCE_DOCUMENT_PATHS]
  - None
  ### Constraints
  - [preserved constraint from OPTIONAL_INSTRUCTIONS]
  - None
  ### Resume Context
  - [resume detail from OPTIONAL_INSTRUCTIONS]
  - None
  ### Settled Decisions
  - [clarified decision from OPTIONAL_INSTRUCTIONS]
  - None
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

Extract: "{tools.phase_resource_example}" → "phase-2a-neo4j-integration"

```text
PHASE_NAME = [basename of the parent directory of PHASE_FILE_PATH]

Display to user: "✓ Located phase file: {{PHASE_NAME}}"
```

**Important**:
- PLAN_NAME identifies which strategic plan to use for context
- PHASE_NAME_PARTIAL is the user input (e.g., "phase-2a")
- PHASE_NAME is the canonical name extracted from file path (e.g., "phase-2a-storage-schema-and-query-translation-integration")
- PLAN_NAME from config is used for all MCP storage operations
- OPTIONAL_INSTRUCTIONS provides only the clarified guidance that remains after phase resolution
- WORKFLOW_GUIDANCE_MARKDOWN reaches the phase agents as the round-0 briefing feedback entry (Step 3)
- All subsequent operations use PHASE_NAME (canonical)

### Step 2: Sync the Plan and Phase

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

### Step 3: Set Up the Run

Runs before Step 4 routes, so every route that reaches a subagent has the review loop, the config
context and the run's guidance.

#### Step 3.1: Initialize and link the review loop

```text
LOOP_RESPONSE = {tools.initialize_loop}
LOOP_ID = [loop_id from LOOP_RESPONSE]

IF LOOP_ID is None or LOOP_ID == "":
  CRITICAL ERROR: "initialize_refinement_loop did not return a valid loop_id"
  DIAGNOSTIC: Show the full LOOP_RESPONSE
  EXIT: Workflow terminated

{tools.link_loop}

LOOP_STATUS = {tools.get_loop_status}

IF LOOP_STATUS does not show the linked phase:
  CRITICAL ERROR: "Loop linking failed - phase-architect and phase-critic will fail"
  DIAGNOSTIC: Show LOOP_STATUS details
  EXIT: Workflow terminated

Display to user: "✓ Review loop {{LOOP_ID}} linked to {{PHASE_NAME}}"
```

`LOOP_ID` is the one review loop of this run: it carries every critic review and every piece of
user feedback the agents read.

#### Step 3.2: Load the project config context

Both agents receive the target project's stack and language evidence, so a polyglot project's
Skeleton Index entries and verify commands are told apart by language.

```text
STANDARDS_TOML_FILES = Glob(.respec-ai/config/standards/*.toml)
LANGUAGE_TOML_FILES = STANDARDS_TOML_FILES excluding universal.toml
STACK_CONFIG = Read(.respec-ai/config/stack.toml) if file exists, else ""
LANGUAGE_CONFIGS = For each file in LANGUAGE_TOML_FILES:
  Read(file) — concatenated content

RUN (Bash): respec-ai language-guidance
IF command exit code == 0:
  LANGUAGE_AUTHORING_NOTES = command output
ELSE:
  LANGUAGE_AUTHORING_NOTES = "Language authoring notes unavailable ([first line of command output]).
    Write Skeleton Index entries in the notation the phase template shows."
  Do NOT terminate the workflow. Continue with the compose block below.

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
  ### Language Authoring Notes
  [LANGUAGE_AUTHORING_NOTES]
```

#### Step 3.3: Record the run's guidance, check bp and reset the counters

```text
IMPLEMENTATION_PLAN_PATH = dirname(PHASE_FILE_PATH) + "/implementation.md"
(The architect writes the build order there; the coding workflow reads it from the same place.)

USER_FEEDBACK_MARKDOWN = "[round 0 | briefing] " + WORKFLOW_GUIDANCE_MARKDOWN
{tools.store_user_feedback}
(Both agents read the run's guidance from this feedback entry.)

RUN (Bash): {tools.bp_preflight_command}
IF command exit code == 0:
  BP_AVAILABLE = true
ELSE:
  BP_AVAILABLE = false
  Do NOT terminate the workflow: the run continues without paid research, and Step 6 tells the user.

REVIEW_ROUND = 0
REPAIR_ROUNDS = 0
UNRESOLVED_CHECKS = []
OPEN_CRITIC_QUESTIONS = []
DESIGN_CHANGE_SD_IDS = []
UNRESOLVED_DIRECTION = none
ARCHITECT_REPORT = none
CRITIC_REPORT = none
{architect_id_setup}
```

### Step 4: Route on the Stage Marker

```text
PHASE_MARKDOWN = {tools.get_document}
STAGE_MARKER = the "### Shape Gate" value in PHASE_MARKDOWN (the document Step 2 synced)

IF STAGE_MARKER == "unshaped":
  Go to Step 5. Decisions already settled in the document are not asked again.

ELIF STAGE_MARKER == "shape-proposed" OR STAGE_MARKER == "shape-amended":
  Display to user: "↻ Resuming the design review from the draft on disk"
  Go to Step 9 (the critic reviews the synced draft), then Step 10.

ELIF STAGE_MARKER == "shape-settled":
  IF OPTIONAL_INSTRUCTIONS explicitly asks to re-open the signed-off design:
    REOPEN_CHOICE = "Re-open the design"
  ELSE:
    {selection_prompt_instructions}
      Header: "Signed Off"
      Question: "{{PHASE_NAME}} is already signed off. What do you want to do?"
      multiSelect: false
      Options: [
        {{"label": "Show the handoff", "description": "Keep the signed-off design and show the next workflow"}},
        {{"label": "Re-open the design", "description": "Mark the phase re-opened and return to the design review"}}
      ]

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 4. Set REOPEN_CHOICE. Continue immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

    REOPEN_CHOICE = [selected option from {selection_response_source}]

  IF REOPEN_CHOICE == "Re-open the design":
    STAGE_MARKER = "shape-amended"
    PHASE_MARKDOWN = PHASE_MARKDOWN with "### Shape Gate" set to STAGE_MARKER
    {tools.store_document}
    Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).
    Go to Step 9 (the critic reviews the signed-off design), then Step 10.
  ELSE:
    Go to Step 12 to show the handoff.

ELSE:
  ERROR: "Unknown stage marker in ### Shape Gate: [STAGE_MARKER]"
  EXIT: Workflow terminated
```

### Step 5: Explore

The architect grounds the design before anything is asked: the plan and its constraints, the
existing code, and local knowledge-base lookups that set each research proposal's cost tier. It
writes its open decisions (OD) and research proposals (RP) into the phase document.

```text
{first_explore}

Go to Step 6.
```

### Step 6: Briefing (TOUCHPOINT)

The user hears what the architect found and settles the consequential decisions and the research
before any draft exists.

#### Step 6.1: Present the briefing

```text
Display ARCHITECT_REPORT's `## For the user` as written: the architect's understanding of the
phase, what exists to build on, the approach sketch, and the research it will use and proposes.

IF BP_AVAILABLE is false:
  Display to user once: "bp is unavailable on this machine, so only existing knowledge-base
  documents are offered. The other research proposals stay open for a later run."
```

#### Step 6.2: Ask the open decisions

```text
PHASE_MARKDOWN = {tools.get_document}
OPEN_DECISIONS = the OD entries in PHASE_MARKDOWN's "### Open Design Decisions", in rank order
ASK_ON_ITS_OWN = []
{briefing_batching}

FOR each OD in OPEN_DECISIONS:
  {selection_prompt_instructions}
    Header: "Design Decision"
    Question: "[OD ID]: [OD title]. Affects: [OD Affects]"
    multiSelect: false
    Options: [
      {{"label": "[Option A name]", "description": "[Option A trade-off]"}},
      {{"label": "[Option B name]", "description": "[Option B trade-off]"}},
      {{"label": "[Option C name, only when the OD has one]", "description": "[Option C trade-off]"}},
      {{"label": "Accept the recommended default for all remaining", "description": "This and every remaining decision get their Recommended option; a recommendation that would end this run is asked on its own"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 6.2. Record the answer. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Accept the recommended default for all remaining":
    FOR this OD and every OD after it:
      IF its Recommended option is Option A of the Design Source OD or of a verify command OD:
        ASK_ON_ITS_OWN.append(the OD)
      ELSE:
        Record "- SD-NNN | source=user | supersedes=[OD ID] | decision=[Recommended option] | rationale=accepted the recommended default | rejected=[the other options] | binding=yes"
    BREAK
  ELSE:
    IF the chosen option is the verify command decision's "Supply the command now":
      IF the user's response does not already carry the command:
        Ask the user for it in one message.
        WAIT for the user's reply.
        DO NOT treat this as workflow completion, cancellation, or failure.
        After the user responds, resume at Step 6.2. Use the reply verbatim. Continue immediately.
        DO NOT explain that the workflow is stopping unless the user asks why.
      Record "- SD-NNN | source=user | supersedes=[OD ID] | decision=Supply the command now: `[the command, verbatim]` | rationale=[the user's reason, or the option's trade-off] | rejected=[the other options] | binding=yes"
    ELSE:
      Record "- SD-NNN | source=user | supersedes=[OD ID] | decision=[chosen option] | rationale=[the user's reason, or the option's trade-off] | rejected=[the other options] | binding=yes"

FOR each OD in ASK_ON_ITS_OWN:
  (Accepting every default never ends the run: an option that ends it takes the user's own choice.)
  {selection_prompt_instructions}
    Header: "Design Decision"
    Question: "[OD ID]: [OD title]. Its recommended option ends this run after the briefing. Affects: [OD Affects]"
    multiSelect: false
    Options: [
      {{"label": "[Option A name]", "description": "[Option A trade-off]"}},
      {{"label": "[Option B name]", "description": "[Option B trade-off]"}},
      {{"label": "[Option C name, only when the OD has one]", "description": "[Option C trade-off]"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 6.2. Record the answer. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the chosen option is the verify command decision's "Supply the command now":
    Ask for the command and record it exactly as the loop above does.
  ELSE:
    Record "- SD-NNN | source=user | supersedes=[OD ID] | decision=[chosen option] | rationale=[the user's reason, or the option's trade-off] | rejected=[the other options] | binding=yes"
```

#### Step 6.3: Ask the research proposals

```text
OFFERED_PROPOSALS = the RP lines in PHASE_MARKDOWN's "### Research Requirements" that carry
  neither [approved] nor [declined], in rank order
IF BP_AVAILABLE is false:
  OFFERED_PROPOSALS = only its lines whose tier is in-kb. The other lines stay unmarked:
  unavailability is not a denial, so a later run with bp available offers them again.
{briefing_batching}

FOR each RP in OFFERED_PROPOSALS:
  {selection_prompt_instructions}
    Header: "Research"
    Question: "[RP ID]: [the question it answers]. Informs: [IDs]. Tier: [tier]"
    multiSelect: false
    Options: [
      {{"label": "Approve", "description": "in-kb: use the existing document, free. synthesis-only: synthesize from the knowledge base. web-research: search the web and add the result to the knowledge base every project on this machine shares"}},
      {{"label": "Deny", "description": "Not researched, and never offered again for this phase"}},
      {{"label": "Edit", "description": "Change what is researched; its cost tier is recomputed"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 6.3. Mark the proposal. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Approve":
    Append " [approved]" to the RP line.
  ELIF the user chose "Deny":
    Append " [declined]" to the RP line.
  ELSE:
    IF the user's response does not already carry the edit:
      Ask the user for it in one message.
      WAIT for the user's reply.
      DO NOT treat this as workflow completion, cancellation, or failure.
      After the user responds, resume at Step 6.3. Use the reply verbatim. Continue immediately.
      DO NOT explain that the workflow is stopping unless the user asks why.
    Rewrite the RP line's question, Technologies, Topics and Query from the user's edit.
    Recompute its tier from local, read-only commands:
      RUN (Bash): best-practices-rag generate-slug --tech "[technologies]" --topics "[topics]"
      RUN (Bash): best-practices-rag check-file-cache --file ".best-practices/[printed slug].md"
        (pass only --file; a model option reports a miss for a document another model wrote)
      RUN (Bash): best-practices-rag query-kb --tech "[technologies]" --topics "[topics]"
      Tier: in-kb:[path] on a cache hit; synthesis-only when fresh results cover every
      technology; web-research on any gap.
    IF the recomputed tier costs more than the tier the user saw (in-kb < synthesis-only < web-research):
      {selection_prompt_instructions}
        Header: "Research Cost"
        Question: "[RP ID] now needs [recomputed tier]. Run it?"
        multiSelect: false
        Options: [
          {{"label": "Approve", "description": "Run it at the new tier"}},
          {{"label": "Deny", "description": "Not researched, and never offered again for this phase"}}
        ]

      WAIT for {selection_response_source}.
      DO NOT treat this as workflow completion, cancellation, or failure.
      After the user responds, resume at Step 6.3. Mark the edited proposal. Continue immediately.
      DO NOT explain that the workflow is stopping unless the user asks why.

      Append " [approved]" or " [declined]" to the rewritten line, per the answer.
    ELSE:
      Append " [approved]" to the rewritten line.
```

#### Step 6.4: Record the briefing answers

```text
PHASE_MARKDOWN = PHASE_MARKDOWN with every SD recorded in Step 6.2 appended to
  "### Settled Design Decisions", each settled OD removed from "### Open Design Decisions",
  and every RP mark from Step 6.3 applied
{tools.store_document}
Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).

IF an SD recorded in Step 6.2 has decision=Option A for the Design Source OD or for a missing verify command OD:
  Display to user what to do before running this workflow again:
  - Design Source, Option A: create the visual design first.
  - Missing verify command, Option A: set [commands].test in .respec-ai/config/standards/<language>.toml.
  Display to user: "Your briefing answers are saved. When that is done, run this workflow again:
  it explores again and asks only what is still open."
  EXIT: The run ends cleanly after the briefing. This is not a failure, and no research or draft runs.
```

#### Step 6.5: Close the briefing

```text
{selection_prompt_instructions}
  Header: "Briefing"
  Question: "Ready for the draft?"
  multiSelect: false
  Options: [
    {{"label": "Continue", "description": "Run the approved research, then draft the design"}},
    {{"label": "Add a research proposal", "description": "Propose research of your own before the draft"}},
    {{"label": "Ask the architect a question", "description": "Relay a question that needs new codebase knowledge"}}
  ]

WAIT for {selection_response_source}.
DO NOT treat this as workflow completion, cancellation, or failure.
After the user responds, resume at Step 6.5. Branch on the choice. Continue immediately.
DO NOT explain that the workflow is stopping unless the user asks why.

IF the user chose "Add a research proposal" OR the user chose "Ask the architect a question":
  IF the user's response does not already carry the proposal or the question:
    Ask the user for it in one message.
    WAIT for the user's reply.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 6.5. Use the reply verbatim. Continue immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

IF the user chose "Add a research proposal":
  Build the proposal from the user's words: the question it answers, what it informs,
  Technologies, Topics and Query. Compute its tier with the three commands in Step 6.3.
  RP_LINE = "- RP-NNN | [question] | informs: [IDs] | Technologies: [list]; Topics: [list]; Query: [query] | tier: [tier] | source=user"
    (RP-NNN is the next number above every RP-NNN in the document)
  IF the tier is synthesis-only or web-research:
    {selection_prompt_instructions}
      Header: "Research Cost"
      Question: "Your proposal needs [tier]. Run it?"
      multiSelect: false
      Options: [
        {{"label": "Approve", "description": "Run it at this tier"}},
        {{"label": "Deny", "description": "Keep it in the ledger as declined"}}
      ]

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 6.5. Mark the new proposal. Continue immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

    Append " [approved]" or " [declined]" to RP_LINE, per the answer.
  ELSE:
    Append " [approved]" to RP_LINE.
  PHASE_MARKDOWN = PHASE_MARKDOWN with RP_LINE added to "### Research Requirements"
  {tools.store_document}
  Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).
  Go back to the start of Step 6.5.

ELIF the user chose "Ask the architect a question":
  IF the user gave direction during the briefing that no SD, RP mark or stored entry records yet:
    USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | briefing] " + [that direction, verbatim]
    {tools.store_user_feedback}
  USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | question] " + [the user's question, verbatim]
  {tools.store_user_feedback}
{indent(explore_again, '  ')}
  Display ARCHITECT_REPORT's `## For the user`: the architect's answer.
  Go to Step 6.2. Decisions already settled and proposals already marked are not asked again.

ELSE:
  IF the user gave direction during the briefing that no SD, RP mark or stored entry records yet:
    USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | briefing] " + [that direction, verbatim]
    {tools.store_user_feedback}
    (The draft architect reads it; direction kept only in this conversation never reaches it.)
  RETURN_TO = "Step 8"
  Go to Step 7.
```

### Step 7: Run Approved Research

The single place research runs. RETURN_TO names where the run goes afterwards: "Step 8" when the
briefing sent it here, "Step 10 follow-up" when the design review did.

#### Step 7.1: Select the approved research

```text
MAX_ACTIVE_BP_WORKERS = 3
MAX_ACTIVE_WEB_RESEARCH_WORKERS = 1
PHASE_MARKDOWN = {tools.get_document}
NEW_READ_LINES = []

FOR each RP line marked [approved] whose tier is in-kb:[path]:
  IF the file at [path] exists AND no "- Read:" line in "### Research Requirements" names it:
    NEW_READ_LINES.append("- Read: `[path]` — informs: [the RP's informs IDs] — Source: in-kb")

RESEARCH_QUEUE = every RP line marked [approved] whose tier is synthesis-only or web-research
  and whose research has no "- Read:" line yet

IF RESEARCH_QUEUE is empty OR BP_AVAILABLE is false:
  IF BP_AVAILABLE is false AND RESEARCH_QUEUE is not empty:
    Display to user once: "bp is unavailable, so the approved research was skipped. Those
    proposals stay approved for a later run."
  Skip the dispatch: go to Step 7.3, which records NEW_READ_LINES and routes by RETURN_TO.
```

#### Step 7.2: Dispatch bp-pipeline

```text
FOR each ITEM in RESEARCH_QUEUE, compute its inputs from local commands only:
  TECH = the RP line's Technologies, comma-separated
  TOPICS = the RP line's Topics, comma-separated
  QUERY = the RP line's Query
  RUN (Bash): best-practices-rag generate-slug --tech "[TECH]" --topics "[TOPICS]"
  OUTPUT_FILE = ".best-practices/[printed slug].md"
  TECH_VERSIONS_JSON and CUTOFF_DATE = read from ~/.config/best-practices-rag/references/tech-versions.md
    for the technologies in TECH
  PRIMARY_QUERY = QUERY with each technology's version from TECH_VERSIONS_JSON, and
    "official documentation" appended
  RUN (Bash): best-practices-rag query-kb --tech "[TECH]" --topics "[TOPICS]"
  Route the coverage fields from that result:
  - full coverage (fresh results cover every technology): COVERED_TECHS and ALL_QUERIED_TECHS
  - partial gap (fresh results, some technologies uncovered): UNCOVERED_TECH, COVERED_TECHS and
    ALL_QUERIED_TECHS
  - full gap (no fresh results): ALL_QUERIED_TECHS only
  LANGUAGES = the [project].languages list in .respec-ai/config/stack.toml
  LANGUAGE_AGNOSTIC = "true" only when that list is empty or absent; then omit LANGUAGES

Deduplicate RESEARCH_QUEUE by OUTPUT_FILE, so two proposals never write one file. DEDUPED holds
each dropped RP with the RP kept for its OUTPUT_FILE.
ACCEPTED = []

Run the synthesis-only items first, at most MAX_ACTIVE_BP_WORKERS at once. Then run the
web-research items one at a time (MAX_ACTIVE_WEB_RESEARCH_WORKERS): a web-research run writes
bp-pipeline's fixed search-result files, so two at once overwrite each other's results. Every
item is dispatched with this one invocation, filled with that item's inputs:

FOR each ITEM, in that order and within those bounds:
{research_dispatch}
  When ITEM's result arrives (do not prompt the user while research runs):
  IF the result contains "BP_PIPELINE_COMPLETE. Output: [path]" AND the file at [path] exists:
    ACCEPTED.append(ITEM with its [path])
  ELSE:
    Display to user: "⚠ Research for [RP ID] did not complete; nothing was recorded for it."
    Record nothing for ITEM and continue with the next item. A failed item never ends the run.
```

#### Step 7.3: Record the research and route

```text
FOR each ITEM in ACCEPTED:
  NEW_READ_LINES.append("- Read: `[path]` — informs: [the RP's informs IDs] — Source: [RP ID]")

FOR each DROPPED RP in DEDUPED whose kept RP is in ACCEPTED:
  NEW_READ_LINES.append("- Read: `[the kept RP's path]` — informs: [the dropped RP's informs IDs] — Source: [the dropped RP ID]")

IF NEW_READ_LINES is not empty:
  PHASE_MARKDOWN = PHASE_MARKDOWN with NEW_READ_LINES added to "### Research Requirements"
  {tools.store_document}
  Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).
  Display to user: "✓ Recorded [count] research document(s)"

IF RETURN_TO == "Step 10 follow-up":
  IF NEW_READ_LINES is not empty OR DESIGN_CHANGE_SD_IDS is not empty OR UNRESOLVED_DIRECTION is set:
    USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | review] " + [the SD IDs in DESIGN_CHANGE_SD_IDS, the new research documents, and UNRESOLVED_DIRECTION when set]
    {tools.store_user_feedback}
    DESIGN_CHANGE_SD_IDS = []
    UNRESOLVED_DIRECTION = none
{indent(revise, '    ')}
    Go to Step 9.
  ELSE:
    Go to Step 10.4, the design review's final prompt.
ELSE:
  Go to Step 8.
```

### Step 8: Draft

The architect drafts the whole design and its `implementation.md` in one pass, on the decisions
the user settled and the research the user approved.

```text
{draft}

PHASE_MARKDOWN = {tools.get_document}
STAGE_MARKER = "shape-proposed"
PHASE_MARKDOWN = PHASE_MARKDOWN with "### Shape Gate" set to STAGE_MARKER
{tools.store_document}
Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).

Go to Step 9.
```

### Step 9: Critic Review and Automatic Repair

The critic reviews every draft before the user sees it, without editing it. Mechanical findings
go back to the architect for at most two repair rounds, and the user is not told about them.
Judgment calls are collected for the design review. This step never prompts the user.

```text
UNRESOLVED_CHECKS = []
PRE_PHASE_LOOP_STATUS = {tools.get_loop_status}
REVIEW_ROUND += 1

{critic_review}
CRITIC_REPORT = the report
OPEN_CRITIC_QUESTIONS = the CQ entries in CRITIC_REPORT's `## Decisions needed`
  (this latest report only; the critic keeps a finding's CQ ID across rounds)

POST_PHASE_LOOP_STATUS = {tools.get_loop_status}
PHASE_FEEDBACK = {tools.get_feedback}

IF retrieval fails OR PHASE_FEEDBACK does not contain "## Iteration [REVIEW_ROUND] -":
  ERROR: "Phase critic did not persist CriticFeedback"
  DIAGNOSTIC: [surface the exact MCP/tool error, or PHASE_FEEDBACK]
  FAIL-CLOSED:
  - Do NOT call decide_loop_next_action
  EXIT: Workflow terminated

IF PRE_PHASE_LOOP_STATUS.status == "initialized" AND POST_PHASE_LOOP_STATUS.status == "initialized":
  ERROR: "Phase critic did not advance loop state"
  DIAGNOSTIC: [surface PRE_PHASE_LOOP_STATUS and POST_PHASE_LOOP_STATUS]
  FAIL-CLOSED:
  - Do NOT call decide_loop_next_action
  EXIT: Workflow terminated

IF PRE_PHASE_LOOP_STATUS.status != "initialized" AND POST_PHASE_LOOP_STATUS.iteration <= PRE_PHASE_LOOP_STATUS.iteration:
  ERROR: "Phase critic did not persist fresh loop feedback"
  DIAGNOSTIC: [surface PRE_PHASE_LOOP_STATUS and POST_PHASE_LOOP_STATUS]
  FAIL-CLOSED:
  - Do NOT call decide_loop_next_action
  EXIT: Workflow terminated

REVIEW_DECISION_RESPONSE = {tools.decide_loop_action}
REVIEW_DECISION = REVIEW_DECISION_RESPONSE.status

IF REVIEW_DECISION == "completed":
  (The latest review has no open mechanical findings.)
  Go to Step 10.

ELIF REVIEW_DECISION == "refine":
  IF REPAIR_ROUNDS < 2:
    REPAIR_ROUNDS += 1
{indent(revise, '    ')}
    Go to Step 9.
  ELSE:
    UNRESOLVED_CHECKS = every finding in the latest review's "### Blockers" in PHASE_FEEDBACK
    Go to Step 10.

ELIF REVIEW_DECISION == "user_input":
  (This does not mean the repairs are spent: the loop's stagnation rule returns user_input before
  any repair has run, so it is repaired like refine while repair rounds remain.)
  IF REPAIR_ROUNDS < 2:
    REPAIR_ROUNDS += 1
{indent(revise, '    ')}
    Go to Step 9.
  ELSE:
    UNRESOLVED_CHECKS = every finding in the latest review's "### Blockers" in PHASE_FEEDBACK
    Go to Step 10.

ELSE:
  ERROR: "Unexpected loop decision"
  DIAGNOSTIC: Show REVIEW_DECISION_RESPONSE
  EXIT: Workflow terminated
```

### Step 10: Design Review (TOUCHPOINT)

The user sees a design the critic has already reviewed. Mechanical issues are repaired, and the
critic's judgment calls arrive as questions. Steps 9 and 10 repeat until the user approves.

#### Step 10.1: Put the draft on disk and present it

```text
REPAIR_ROUNDS = 0
(Every send-back from this design review starts a fresh repair budget.)
PHASE_MARKDOWN = {tools.get_document}
Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).
LAST_WRITTEN_PHASE_MARKDOWN = PHASE_MARKDOWN

Display ARCHITECT_REPORT's `## For the user` when this run has one (a resumed run has no
architect report yet).
IF PHASE_MARKDOWN contains "#### UX Contract":
  Display to user: "→ This design includes a UX Contract under Design Shape - Additional Sections.
  Review its Route Index, Required States, Interaction Flows (each needs an explicit, mechanically
  checkable pass condition), Accessibility Requirements, Breakpoints, and Design Source."
Display CRITIC_REPORT's `## For the user`.
Display to user: "The draft is at [PHASE_FILE_PATH] and its build order at
[IMPLEMENTATION_PLAN_PATH]. To edit phase.md by hand, wait for the final prompt of this review.
Do not rename, add or delete any '##' or '###' heading, and do not add a bare '---' line inside a
section: the parser drops both silently."
```

#### Step 10.2: Ask the open questions

```text
OPEN_DECISIONS = the OD entries in PHASE_MARKDOWN's "### Open Design Decisions", in rank order
  (the draft follows each one's Recommended option)
QUESTIONS = the CQ entries in OPEN_CRITIC_QUESTIONS that no SD in "### Settled Design Decisions"
  supersedes, in rank order
  (Option A keeps the design as drafted; Option B is the critic's alternative)
NEW_PROPOSALS = []
IF BP_AVAILABLE:
  NEW_PROPOSALS = every RP line in "### Research Requirements" with neither [approved] nor
  [declined]: normally the one new gap from the draft or a revise
APPROVED_PROPOSALS = []
{review_batching}

FOR each entry in OPEN_DECISIONS, then in QUESTIONS:
  {selection_prompt_instructions}
    Header: "Design Decision"
    Question: "[OD or CQ ID]: [title]. Affects: [Affects]"
    multiSelect: false
    Options: [
      {{"label": "[Option A name]", "description": "[Option A trade-off]"}},
      {{"label": "[Option B name]", "description": "[Option B trade-off]"}},
      {{"label": "[Option C name, only when the entry has one]", "description": "[Option C trade-off]"}},
      {{"label": "Accept the recommended default for all remaining", "description": "This and every remaining question get their Recommended option"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 10.2. Record the answer. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Accept the recommended default for all remaining":
    FOR this entry and every entry after it:
      Record "- SD-NNN | source=user | supersedes=[OD or CQ ID] | decision=[Recommended option] | rationale=accepted the recommended default | rejected=[the other options] | binding=yes"
      IF the entry is a CQ whose Recommended option is Option B:
        DESIGN_CHANGE_SD_IDS.append([the new SD ID])
    BREAK
  ELSE:
    Record "- SD-NNN | source=user | supersedes=[OD or CQ ID] | decision=[chosen option] | rationale=[the user's reason, or the option's trade-off] | rejected=[the other options] | binding=yes"
    IF the entry is an OD answered with anything but its Recommended option, OR a CQ answered with Option B:
      DESIGN_CHANGE_SD_IDS.append([the new SD ID])

FOR each RP in NEW_PROPOSALS:
  {selection_prompt_instructions}
    Header: "Research"
    Question: "[RP ID]: [the question it answers]. Informs: [IDs]. Tier: [tier]"
    multiSelect: false
    Options: [
      {{"label": "Approve", "description": "Run it, then the architect revises the design with the result"}},
      {{"label": "Deny", "description": "Not researched, and never offered again for this phase"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 10.2. Mark the proposal. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Approve":
    Append " [approved]" to the RP line.
    APPROVED_PROPOSALS.append(RP)
  ELSE:
    Append " [declined]" to the RP line.

IF UNRESOLVED_CHECKS is not empty:
  Display UNRESOLVED_CHECKS: the mechanical findings two automatic repairs did not resolve, each verbatim.
  {selection_prompt_instructions}
    Header: "Unresolved Checks"
    Question: "The critic's mechanical checks still fail after two automatic repairs. How do you want to handle them?"
    multiSelect: false
    Options: [
      {{"label": "Send back with direction", "description": "Tell the architect how to resolve them"}},
      {{"label": "Accept as-is", "description": "Recorded as your decision; the critic never raises these findings again"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 10.2. Record the answer. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Accept as-is":
    Record "- SD-NNN | source=user | supersedes=unresolved-checks | decision=accept as-is: [each finding verbatim] | rationale=[the user's reason, or accepted at design review] | binding=yes"
  ELSE:
    IF the user's response does not already carry the direction:
      Ask the user how the architect is to resolve the findings.
      WAIT for the user's reply.
      DO NOT treat this as workflow completion, cancellation, or failure.
      After the user responds, resume at Step 10.2. Use the reply verbatim. Continue immediately.
      DO NOT explain that the workflow is stopping unless the user asks why.
    UNRESOLVED_DIRECTION = [the user's direction, verbatim, with the findings it addresses]

IF any SD or RP mark was recorded above:
  PHASE_MARKDOWN = PHASE_MARKDOWN with every SD recorded above appended to
    "### Settled Design Decisions", each settled OD removed from "### Open Design Decisions",
    and every RP mark applied
  {tools.store_document}
  Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).
  LAST_WRITTEN_PHASE_MARKDOWN = PHASE_MARKDOWN
```

#### Step 10.3: Send design-changing answers back to the architect

```text
IF APPROVED_PROPOSALS is not empty:
  RETURN_TO = "Step 10 follow-up"
  Go to Step 7. Its follow-up sends the new research, DESIGN_CHANGE_SD_IDS and UNRESOLVED_DIRECTION
  to the architect in one revise.

IF DESIGN_CHANGE_SD_IDS is not empty OR UNRESOLVED_DIRECTION is set:
  USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | review] " + [the SD IDs in DESIGN_CHANGE_SD_IDS, and UNRESOLVED_DIRECTION when set]
  {tools.store_user_feedback}
  DESIGN_CHANGE_SD_IDS = []
  UNRESOLVED_DIRECTION = none
{indent(revise, '  ')}
  Go to Step 9.
```

#### Step 10.4: Final prompt

```text
{selection_prompt_instructions}
  Header: "Design Review"
  Question: "How do you want to proceed with this design?"
  multiSelect: false
  Options: [
    {{"label": "Approve the design", "description": "Go to sign-off"}},
    {{"label": "Tell me what to change", "description": "The architect revises the design, then the critic reviews it again"}},
    {{"label": "I edited phase.md myself", "description": "Validate and record your edits, then the critic reviews them"}},
    {{"label": "Ask the architect a question", "description": "Relay a question that needs new codebase knowledge"}}
  ]

WAIT for {selection_response_source}.
DO NOT treat this as workflow completion, cancellation, or failure.
After the user responds, resume at Step 10.4. Set REVIEW_CHOICE. Continue immediately.
DO NOT explain that the workflow is stopping unless the user asks why.

REVIEW_CHOICE = [selected option from {selection_response_source}]
DISK_MARKDOWN = Read PHASE_FILE_PATH (Use Read tool)

IF DISK_MARKDOWN differs from LAST_WRITTEN_PHASE_MARKDOWN OR REVIEW_CHOICE == "I edited phase.md myself":
  Go to Step 10.5 first, whatever the choice: a change request never discards a hand edit.
ELSE:
  Go to Step 10.6.
```

#### Step 10.5: Validate and record a hand edit

```text
RAW_EDITED_MARKDOWN = DISK_MARKDOWN
VALIDATION_ATTEMPTS = 0
CONTENT_TO_VALIDATE = RAW_EDITED_MARKDOWN
VALIDATION_RESULT = {tools.validate_document}

WHILE VALIDATION_RESULT.status != "completed" AND VALIDATION_ATTEMPTS < 3:
  Display to user: VALIDATION_RESULT.message

  {selection_prompt_instructions}
    Header: "Content Would Be Lost"
    Question: "Some of your edits would be silently dropped. How do you want to proceed?"
    multiSelect: false
    Options: [
      {{"label": "Let me fix it and try again", "description": "Attempt [VALIDATION_ATTEMPTS + 1] of 3"}},
      {{"label": "Drop those edits and continue", "description": "Proceed with the version the parser accepts; the flagged content is discarded"}},
      {{"label": "Abort and send it back to the architect", "description": "Keep the stored design; the architect revises it with the validation report"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 10.5. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Let me fix it and try again":
    VALIDATION_ATTEMPTS += 1
    (The user edits PHASE_FILE_PATH again outside this prompt.)
    RAW_EDITED_MARKDOWN = Read PHASE_FILE_PATH (Use Read tool)
    CONTENT_TO_VALIDATE = RAW_EDITED_MARKDOWN
    VALIDATION_RESULT = {tools.validate_document}
    CONTINUE loop
  ELIF the user chose "Drop those edits and continue":
    BREAK  (proceed with RAW_EDITED_MARKDOWN as-is; the flagged headings are known to be lost)
  ELSE:
    USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | review] The user abandoned a hand edit of phase.md. Validation report: " + VALIDATION_RESULT.message
    {tools.store_user_feedback}
{indent(revise, '    ')}
    Go to Step 9.

IF VALIDATION_ATTEMPTS == 3 AND VALIDATION_RESULT.status != "completed":
  ERROR: "validate_document still reports content loss after 3 attempts"
  DIAGNOSTIC: Show VALIDATION_RESULT.message
  EXIT: Workflow terminated

Diff RAW_EDITED_MARKDOWN against LAST_WRITTEN_PHASE_MARKDOWN per (H2, H3) heading.
FOR each heading with a changed value, append to "### Settled Design Decisions":
  "- SD-NNN | source=user-edit | section=[H2 > H3] | decision=[one-line summary of the change] | binding=yes"
RECONCILED_PHASE_MARKDOWN = RAW_EDITED_MARKDOWN with the appended SD entries
Set "### Shape Gate" in RECONCILED_PHASE_MARKDOWN back to STAGE_MARKER: a hand edit is not a
sign-off, and the store below writes whatever marker it is given.

**Frozen fields are editable here and only here.** If Objectives/Scope/Dependencies/
Deliverables changed, this is the sanctioned human exception: the freeze binds agents only
(docs/phase-refactor/decisions.md "Frozen fields are repaired, not deleted").

{tools.store_document_user_edit}
Write RECONCILED_PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool), so MCP and disk agree.
LAST_WRITTEN_PHASE_MARKDOWN = RECONCILED_PHASE_MARKDOWN

IF REVIEW_CHOICE == "Tell me what to change" OR REVIEW_CHOICE == "Ask the architect a question":
  Go to Step 10.6.
ELSE:
  Go to Step 9. The critic reviews the edited design.
```

#### Step 10.6: Act on the choice

```text
IF REVIEW_CHOICE == "Tell me what to change" OR REVIEW_CHOICE == "Ask the architect a question":
  IF the user's response does not already carry the change or the question:
    Ask the user for it in one message.
    WAIT for the user's reply.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 10.6. Use the reply verbatim. Continue immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

IF REVIEW_CHOICE == "Tell me what to change":
  USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | review] " + [the user's direction, verbatim]
  {tools.store_user_feedback}
{indent(revise, '  ')}
  Go to Step 9.

ELIF REVIEW_CHOICE == "Ask the architect a question":
  USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | question] " + [the user's question, verbatim]
  {tools.store_user_feedback}
{indent(revise, '  ')}
  Display ARCHITECT_REPORT's `## For the user`: the architect's answer.
  IF the report's `persisted` is nothing:
    Go to Step 10.4, the final prompt.
  ELSE:
    Go to Step 9. The answer changed the design, so the critic reviews it.

ELSE:
  Go to Step 11.
```

### Step 11: Sign-off (TOUCHPOINT)

The user answers whatever is still open, then signs off. Only then are skeletons written, the
design marked settled, and a commit offered.

#### Step 11.1: Settle what is still open

```text
PHASE_MARKDOWN = {tools.get_document}
REMAINING = the OD entries in "### Open Design Decisions", then the CQ entries in
  OPEN_CRITIC_QUESTIONS that no SD supersedes
{review_batching}

FOR each entry in REMAINING:
  {selection_prompt_instructions}
    Header: "Open Decision"
    Question: "[OD or CQ ID]: [title]. Affects: [Affects]"
    multiSelect: false
    Options: [
      {{"label": "[Option A name]", "description": "[Option A trade-off]"}},
      {{"label": "[Option B name]", "description": "[Option B trade-off]"}},
      {{"label": "[Option C name, only when the entry has one]", "description": "[Option C trade-off]"}},
      {{"label": "Accept the recommended default for all remaining", "description": "This and every remaining question get their Recommended option"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 11.1. Record the answer. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Accept the recommended default for all remaining":
    FOR this entry and every entry after it:
      Record "- SD-NNN | source=user | supersedes=[OD or CQ ID] | decision=[Recommended option] | rationale=accepted the recommended default | rejected=[the other options] | binding=yes"
      IF the entry is a CQ whose Recommended option is Option B:
        DESIGN_CHANGE_SD_IDS.append([the new SD ID])
    BREAK
  ELSE:
    Record "- SD-NNN | source=user | supersedes=[OD or CQ ID] | decision=[chosen option] | rationale=[the user's reason, or the option's trade-off] | rejected=[the other options] | binding=yes"
    IF the entry is an OD answered with anything but its Recommended option, OR a CQ answered with Option B:
      DESIGN_CHANGE_SD_IDS.append([the new SD ID])

IF REMAINING is not empty:
  PHASE_MARKDOWN = PHASE_MARKDOWN with every SD recorded above appended to
    "### Settled Design Decisions" and each settled OD removed from "### Open Design Decisions"
  {tools.store_document}
  Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).

IF DESIGN_CHANGE_SD_IDS is not empty:
  USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | sign-off] " + [the SD IDs in DESIGN_CHANGE_SD_IDS]
  {tools.store_user_feedback}
  DESIGN_CHANGE_SD_IDS = []
{indent(revise, '  ')}
  Go to Step 9, then the design review again.
```

#### Step 11.2: Ask for the sign-off

```text
{selection_prompt_instructions}
  Header: "Sign-off"
  Question: "Sign off this design?"
  multiSelect: false
  Options: [
    {{"label": "Sign off and commit", "description": "Write skeletons, mark the design settled, and commit the files this run wrote with your hooks enabled"}},
    {{"label": "Sign off without committing", "description": "Write skeletons and mark the design settled; leave the files uncommitted"}},
    {{"label": "Go back to design review", "description": "Return to the design review"}}
  ]

WAIT for {selection_response_source}.
DO NOT treat this as workflow completion, cancellation, or failure.
After the user responds, resume at Step 11.2. Set SIGN_OFF_CHOICE. Continue immediately.
DO NOT explain that the workflow is stopping unless the user asks why.

SIGN_OFF_CHOICE = [selected option from {selection_response_source}]
IF SIGN_OFF_CHOICE == "Go back to design review":
  Go to Step 10.
```

#### Step 11.3: Confirm implementation.md exists

```text
IF no file exists at IMPLEMENTATION_PLAN_PATH:
  USER_FEEDBACK_MARKDOWN = "[round REVIEW_ROUND | sign-off] implementation.md is missing at [IMPLEMENTATION_PLAN_PATH]. Write it from the design."
  {tools.store_user_feedback}
{indent(revise, '  ')}
  IF no file exists at IMPLEMENTATION_PLAN_PATH:
    ERROR: "implementation.md is still missing at IMPLEMENTATION_PLAN_PATH after one revise"
    DIAGNOSTIC: [the architect report's `## Status`]
    EXIT: Workflow terminated. The phase is not signed off.
```

#### Step 11.4: Materialize skeletons

Real files are written only from the design the user signed off, and before the design is marked
settled. Skeleton writes are create-only (docs/phase-refactor/decisions.md "Skeletons are written
into the real codebase" and "Skeleton writes are create-only").

```text
PHASE_MARKDOWN = {tools.get_document}
PHASE_DIR = dirname(PHASE_FILE_PATH)
SKELETON_INDEX_SCRATCH = f"{{PHASE_DIR}}/.skeleton-index.md"
TEST_LIST_SCRATCH = f"{{PHASE_DIR}}/.test-list.md"

Write PHASE_MARKDOWN's "### Skeleton Index" section content to
SKELETON_INDEX_SCRATCH (Use Write tool).
Write PHASE_MARKDOWN's "### Test List" section content to
TEST_LIST_SCRATCH (Use Write tool).

RUN (Bash): respec-ai materialize-skeletons --skeleton-index-file {{SKELETON_INDEX_SCRATCH}} --test-list-file {{TEST_LIST_SCRATCH}}

MATERIALIZE_RESULT = [parsed JSON from command stdout]

IF command exit code != 0:
  ERROR: "Skeleton materialization failed"
  DIAGNOSTIC: [surface the command's stdout and stderr]
  FAIL-CLOSED:
  - Do NOT sign off the phase
  EXIT: Workflow terminated

MATERIALIZATION_SDS = []
MERGE_PATHS = []

FOR each CONFLICT in MATERIALIZE_RESULT.reconciliation_needed:
  Display to user: "{{CONFLICT.path}} already exists.
  Existing: {{CONFLICT.existing_signatures}}
  Designed: {{CONFLICT.designed_signatures}}"

  {selection_prompt_instructions}
    Header: "Skeleton Conflict"
    Question: "{{CONFLICT.path}} already exists. How do you want to reconcile it with the signed-off design?"
    multiSelect: false
    Options: [
      {{"label": "Accept the design change", "description": "Record a Settled Decision; the file is reconciled during implementation"}},
      {{"label": "Keep the existing signature", "description": "Update Skeleton Index to match what is actually on disk"}},
      {{"label": "Merge: add only the new members", "description": "Append genuinely new members to the existing file; existing members are left untouched"}}
    ]

  WAIT for {selection_response_source}.
  DO NOT treat this as workflow completion, cancellation, or failure.
  After the user responds, resume at Step 11.4 with the next conflict. Continue immediately.
  DO NOT explain that the workflow is stopping unless the user asks why.

  IF the user chose "Accept the design change":
    MATERIALIZATION_SDS.append("- SD-NNN | source=user | decision=accept design change at {{CONFLICT.path}} | rationale=existing file differs from Skeleton Index; reconciled during implementation | binding=yes")

  ELIF the user chose "Keep the existing signature":
    Update the "### Skeleton Index" entries for {{CONFLICT.path}} in PHASE_MARKDOWN to match CONFLICT.existing_signatures
    MATERIALIZATION_SDS.append("- SD-NNN | source=user | decision=keep existing signature at {{CONFLICT.path}} | rationale=matches what is already implemented | binding=yes")

  ELSE:
    MERGE_PATHS.append(CONFLICT.path)
    MATERIALIZATION_SDS.append("- SD-NNN | source=user | decision=merge new members into {{CONFLICT.path}} | rationale=existing members kept, only genuinely new ones added | binding=yes")

IF MATERIALIZE_RESULT.unmaterialized_paths is not empty:
  Display to user: "⚠ These Skeleton Index / Test List paths could not be materialized
  and were NOT written: {{MATERIALIZE_RESULT.unmaterialized_paths}}"
  FOR each UNMATERIALIZED in MATERIALIZE_RESULT.unmaterialized_paths:
    MATERIALIZATION_SDS.append("- SD-NNN | source=materializer | decision=unmaterialized at {{UNMATERIALIZED.path}} | rationale={{UNMATERIALIZED.reason}} | binding=yes")

IF MATERIALIZE_RESULT.unintrospectable_paths is not empty:
  Display to user: "⚠ These paths already exist and the language has no
  introspection capability yet, so they were left untouched (create-only degrade,
  never overwritten, never merged automatically): {{MATERIALIZE_RESULT.unintrospectable_paths}}"
  FOR each PATH in MATERIALIZE_RESULT.unintrospectable_paths:
    MATERIALIZATION_SDS.append("- SD-NNN | source=materializer | decision=unintrospectable at {{PATH}} | rationale=pre-existing file, language has no signature-introspection capability yet; reconcile manually or during implementation | binding=yes")

IF MERGE_PATHS is not empty:
  RUN (Bash): respec-ai materialize-skeletons --skeleton-index-file {{SKELETON_INDEX_SCRATCH}} --test-list-file {{TEST_LIST_SCRATCH}} --merge-paths {{",".join(MERGE_PATHS)}}
  MERGE_RESULT = [parsed JSON from command stdout]

  IF MERGE_RESULT.unresolved_signature_conflicts is not empty:
    Display to user: "⚠ These merge-selected members already exist with a different
    signature than designed, so they were left untouched: {{MERGE_RESULT.unresolved_signature_conflicts}}"
    MATERIALIZATION_SDS.append("- SD-NNN | source=materializer | decision=unresolved signature conflict left untouched at merge time: {{MERGE_RESULT.unresolved_signature_conflicts}} | rationale=reconciled during implementation | binding=yes")

  IF MERGE_RESULT.unintrospectable_paths is not empty:
    Display to user: "⚠ These merge-selected paths have no introspection capability
    for their language, so no merge was attempted: {{MERGE_RESULT.unintrospectable_paths}}"
    MATERIALIZATION_SDS.append("- SD-NNN | source=materializer | decision=merge skipped, unintrospectable: {{MERGE_RESULT.unintrospectable_paths}} | rationale=language has no signature-introspection capability yet | binding=yes")

WRITTEN_PATHS = MATERIALIZE_RESULT.written_skeletons + MATERIALIZE_RESULT.written_tests + (MERGE_RESULT.merged_paths if MERGE_PATHS else [])
```

#### Step 11.5: Mark the design settled

```text
PHASE_MARKDOWN = PHASE_MARKDOWN with:
- MATERIALIZATION_SDS appended to "### Settled Design Decisions" (each with the next SD number)
- "## Additional Details > ### Implementation Plan References" containing
  "- Constraint: `{{IMPLEMENTATION_PLAN_PATH}}`" (create the section if absent; add the entry
  only when it is not already present)
- "### Shape Gate" set to "shape-settled"
STAGE_MARKER = "shape-settled"
{tools.store_document}
Write PHASE_MARKDOWN to PHASE_FILE_PATH (Use Write tool).

Display to user: "✓ Design signed off; [count of WRITTEN_PATHS] skeleton/test file(s) written"
```

#### Step 11.6: Commit, only when the user chose it

```text
IF SIGN_OFF_CHOICE == "Sign off and commit":
  RUN (Bash): git add -- {{PHASE_FILE_PATH}} {{IMPLEMENTATION_PLAN_PATH}} {{" ".join(WRITTEN_PATHS)}}
  (Stage exactly these files: never everything, and never the two scratch files.)
  RUN (Bash): git commit -F - <<'EOF'
  design: sign off {{PHASE_NAME}}
  EOF
  IF the commit fails (for example, a hook rejects it):
    Display the hook output to the user and leave the files uncommitted. Never retry with hooks disabled.
  ELSE:
    Display to user: "✓ Committed the files this run wrote"
ELSE:
  Display to user: "✓ Signed off. The files this run wrote are left uncommitted."

Go to Step 12.
```

### Step 12: Store and Hand Off

═══════════════════════════════════════════════
MANDATORY PHASE FILE STORAGE RESTRICTION
═══════════════════════════════════════════════
The phase document reaches disk only through these writes:
1. MCP storage, through store_document, at every step that records something.
2. The disk mirror: PHASE_FILE_PATH, written with the same markdown after every orchestrator
   store, and the hand-edit write-back at Step 10.5.
3. The two skeleton scratch files at Step 11.4 (SKELETON_INDEX_SCRATCH and TEST_LIST_SCRATCH,
   under PHASE_DIR). The skeleton command reads them and writes create-only skeletons to the
   paths named in "### Skeleton Index" and "### Test List"; it never writes phase.md.
4. The architect's own write of implementation.md at IMPLEMENTATION_PLAN_PATH.
5. Platform storage (Step 12.2 below).

Do NOT:
- Write phase.md or any other .md file to disk outside the writes listed above
- Create backup or checkpoint files

VIOLATION: Writing any phase file outside the writes listed above.
═══════════════════════════════════════════════

#### Step 12.1: Retrieve the final phase from MCP

```text
FINAL_PHASE_RESPONSE = {tools.get_document}
FINAL_PHASE_MARKDOWN = FINAL_PHASE_RESPONSE.message
```

#### Step 12.2: Save to the external platform

```text
Ensure directory exists:
{tools.phase_location_setup}

Use {tools.create_phase_tool} to store the phase:

Title: Phase: [PHASE_NAME]
Content: [FINAL_PHASE_MARKDOWN]
Labels: phase, architecture
```

**Important**: Use FINAL_PHASE_MARKDOWN from MCP, NOT raw architect output. This ensures immutable
initial fields (objectives, scope, dependencies, deliverables) are preserved.

#### Step 12.3: Completion contract and handoff

```text
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Display: "✅  PHASE SIGNED OFF"
Display: "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

Completion contract (required in final response):
1. phase_file_path
2. phase_status
3. implementation_plan_path

Display:
"✅ Phase signed off. Next: run the implementation workflow"
{tools.code_command_invocation}
```

## Phase Name Normalization Rules

**IMPORTANT:** Phase names are automatically normalized to kebab-case:

**File System → MCP Normalization:**
- Convert to lowercase: `Phase-1` → `phase-1`
- Replace spaces/underscores with hyphens: `phase 1` → `phase-1`
- Remove special characters: `phase-1!` → `phase-1`
- Collapse multiple hyphens: `phase--1` → `phase-1`
- Strip leading/trailing hyphens: `-phase-1-` → `phase-1`

**Critical:** The H1 header in phase markdown MUST match the normalized bundle directory name:
- Bundle directory: `phase-2a-storage-schema-and-query-translation-integration/phase.md`
- H1 header: `# Phase: phase-2a-storage-schema-and-query-translation-integration`
- Mismatch will cause storage/retrieval failures

**Phase-architect agents:** Generate H1 headers in kebab-case to match the bundle directory name.
"""
