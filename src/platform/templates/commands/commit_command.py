from src.platform.models import CommitCommandTools


def generate_commit_command_template(tools: CommitCommandTools) -> str:
    return f"""---
allowed-tools: {tools.tools_yaml}
argument-hint: [commit-kind]
description: Build and execute standardized respec workflow commits
---

# respec-commit Command

## Purpose
Build the standardized commit subject/body for a known respec workflow commit point and execute the git commit mechanics in the active orchestration context.

## Invocation Context

The invoking workflow sets these context values before running this command:
- `COMMIT_KIND`: `phase1-checkpoint`, `phase2-checkpoint`, or `final`
- `COMMIT_WORKFLOW_KIND`: `code` or `patch`
- `ALLOW_EMPTY`: `true` or `false`

The active context also contains the relevant loop variables and feedback markdown from the invoking workflow. This command uses that context directly. It does not retrieve MCP feedback.

═══════════════════════════════════════════════
TOOL INVOCATION
═══════════════════════════════════════════════
You have access to Bash only.

When instructions say "RUN command", execute the command with Bash.
Do NOT describe what you would do. Execute the command.
═══════════════════════════════════════════════

═══════════════════════════════════════════════
MANDATORY BOUNDARY
═══════════════════════════════════════════════
- Do NOT edit source files.
- Do NOT edit test files.
- Do NOT run pre-commit.
- Do NOT retrieve MCP feedback.
- Do NOT decide workflow branch outcomes.
- Do NOT add attribution trailers, including Co-Authored-By, Signed-off-by, Generated-by, or similar.
═══════════════════════════════════════════════

## Workflow

### Step 1: Resolve Commit Inputs

```text
RAW_ARGS = trimmed command arguments

IF RAW_ARGS contains a non-empty first token:
  COMMIT_KIND = [first token normalized to lowercase]
ELSE:
  Use existing COMMIT_KIND from current context.

IF COMMIT_KIND not in {{phase1-checkpoint, phase2-checkpoint, final}}:
  ERROR: "Unsupported COMMIT_KIND"
  EXIT: Commit failed

IF COMMIT_WORKFLOW_KIND not in {{code, patch}}:
  ERROR: "COMMIT_WORKFLOW_KIND must be code or patch"
  EXIT: Commit failed

IF ALLOW_EMPTY not in {{true, false}}:
  ERROR: "ALLOW_EMPTY must be true or false"
  EXIT: Commit failed
```

### Step 2: Build Message Metadata

```text
IF COMMIT_KIND == "phase1-checkpoint":
  FEEDBACK_SOURCE = PHASE1_FEEDBACK
  SCORE = [extract latest Overall Score from PHASE1_FEEDBACK, fallback CODING_SCORE]
  SUMMARY = [extract latest Assessment Summary from PHASE1_FEEDBACK]
  ACCOMPLISHED = [extract concise accomplished outcomes from PHASE1_FEEDBACK or coder handoff report]
  KEY_ISSUES = [extract top key issues from PHASE1_FEEDBACK]
  BLOCKERS_ACTIVE = PHASE1_FEEDBACK contains any of:
    "[Severity:P0]", "severity=P0", "**[P0]**", "[BLOCKING]"
  IF BLOCKERS_ACTIVE:
    REVIEW_STATUS = "blocked by active blockers"
  ELIF CODING_DECISION == "complete":
    REVIEW_STATUS = "ready for completion gate"
  ELSE:
    REVIEW_STATUS = "below completion threshold"
  IF COMMIT_WORKFLOW_KIND == "patch":
    SUBJECT = "[WIP] patch {{PHASE_NAME}} [Phase 1 iter {{CODING_ITERATION}}]"
    CONTEXT_CHANGE = "Change: {{REQUEST_SUMMARY}}"
  ELSE:
    SUBJECT = "[WIP] {{PHASE_NAME}} [Phase 1 iter {{CODING_ITERATION}}]"
    CONTEXT_CHANGE = "Change: None"
  REVIEW_BLOCK = compose:
    Review Score: {{SCORE}}/100
    Review Status: {{REVIEW_STATUS}}
    Decision: {{CODING_DECISION}}
  CONTEXT_BLOCK = compose:
    {{CONTEXT_CHANGE}}
    Phase: {{PHASE_NAME}}
    Loop: Phase 1 (coding_loop_id={{CODING_LOOP_ID}})
  SOURCE_BLOCK = "MCP consolidated CriticFeedback"

IF COMMIT_KIND == "phase2-checkpoint":
  FEEDBACK_SOURCE = STANDARDS_FEEDBACK
  SCORE = [extract latest Overall Score from STANDARDS_FEEDBACK, fallback STANDARDS_SCORE]
  SUMMARY = [extract latest Assessment Summary from STANDARDS_FEEDBACK]
  ACCOMPLISHED = [extract concise accomplished outcomes from STANDARDS_FEEDBACK or coder handoff report]
  KEY_ISSUES = [extract top key issues from STANDARDS_FEEDBACK]
  BLOCKERS_ACTIVE = STANDARDS_FEEDBACK contains any of:
    "[Severity:P0]", "severity=P0", "**[P0]**", "[BLOCKING]"
  IF BLOCKERS_ACTIVE:
    REVIEW_STATUS = "blocked by active blockers"
  ELIF STANDARDS_DECISION == "complete":
    REVIEW_STATUS = "ready for completion gate"
  ELSE:
    REVIEW_STATUS = "below completion threshold"
  IF COMMIT_WORKFLOW_KIND == "patch":
    SUBJECT = "[WIP] patch {{PHASE_NAME}} [Phase 2 iter {{STANDARDS_ITERATION}}]"
    CONTEXT_CHANGE = "Change: {{REQUEST_SUMMARY}}"
  ELSE:
    SUBJECT = "[WIP] {{PHASE_NAME}} [Phase 2 iter {{STANDARDS_ITERATION}}]"
    CONTEXT_CHANGE = "Change: None"
  REVIEW_BLOCK = compose:
    Review Score: {{SCORE}}/100
    Review Status: {{REVIEW_STATUS}}
    Decision: {{STANDARDS_DECISION}}
  CONTEXT_BLOCK = compose:
    {{CONTEXT_CHANGE}}
    Phase: {{PHASE_NAME}}
    Loop: Phase 2 standards (loop_id={{STANDARDS_LOOP_ID}})
  SOURCE_BLOCK = "coding-standards-reviewer CriticFeedback"

IF COMMIT_KIND == "final":
  FEEDBACK_SOURCE = FINAL_FEEDBACK
  SCORE = [extract latest Overall Score from FINAL_FEEDBACK]
  SUMMARY = [extract latest Assessment Summary from FINAL_FEEDBACK]
  ACCOMPLISHED = [extract concise accomplished outcomes from FINAL_FEEDBACK or coder handoff report]
  KEY_ISSUES = [extract top key issues from FINAL_FEEDBACK]
  IF COMMIT_WORKFLOW_KIND == "patch":
    SUBJECT = "fix: complete {{REQUEST_SUMMARY}}"
    CONTEXT_CHANGE = "Change: {{REQUEST_SUMMARY}}"
  ELSE:
    SUBJECT = "feat: complete {{PHASE_NAME}}"
    CONTEXT_CHANGE = "Change: None"
  REVIEW_BLOCK = compose:
    Review Score: {{SCORE}}/100
    Finalization Source: {{FINALIZATION_DECISION_SOURCE}}
    Final Loop: {{FINAL_LOOP_LABEL}} (loop_id={{FINAL_LOOP_ID}})
    Completion Gate: {{COMPLETION_GATE_STATUS}}
    Completion Gate Summary: {{COMPLETION_GATE_SUMMARY}}
  CONTEXT_BLOCK = compose:
    {{CONTEXT_CHANGE}}
    Phase: {{PHASE_NAME}}
  SOURCE_BLOCK = FINAL_SOURCE

IF SUMMARY is empty:
  SUMMARY = "None"
IF ACCOMPLISHED is empty:
  ACCOMPLISHED = "None"
IF KEY_ISSUES is empty:
  KEY_ISSUES = "None"
```

### Step 3: Build Commit Message

```text
COMMIT_MESSAGE_BLOCK = compose exactly:
  {{SUBJECT}}

  Summary:
  {{SUMMARY}}

  Review:
  {{REVIEW_BLOCK}}

  Accomplished:
  {{ACCOMPLISHED}}

  Remaining Issues/Blockers:
  {{KEY_ISSUES}}

  Context:
  {{CONTEXT_BLOCK}}

  Source:
  {{SOURCE_BLOCK}}
```

Commit message rules:
- Use exactly COMMIT_MESSAGE_BLOCK as the commit body.
- Do NOT append attribution trailers.
- Preserve the displayed section order.
- Preserve empty metadata sections as `None`.

### Step 4: Commit

```text
STATUS_OUTPUT = RUN git status --porcelain
EMPTY_COMMIT_USED = false

RUN git add -A

IF STATUS_OUTPUT is empty AND ALLOW_EMPTY == false:
  ERROR: "No changes to commit and ALLOW_EMPTY=false"
  EXIT: Commit failed

IF STATUS_OUTPUT is empty AND ALLOW_EMPTY == true:
  EMPTY_COMMIT_USED = true
  RUN git commit --allow-empty --no-verify -F - <<'EOF'
  {{COMMIT_MESSAGE_BLOCK}}
  EOF

IF STATUS_OUTPUT is not empty:
  RUN git commit --no-verify -F - <<'EOF'
  {{COMMIT_MESSAGE_BLOCK}}
  EOF
```

### Step 5: Remove Prohibited Trailers

```text
AMENDED = false
LATEST_COMMIT_BODY = RUN git log -1 --pretty=%B

IF LATEST_COMMIT_BODY contains any prohibited attribution trailer:
  AMENDED = true
  RUN git commit --amend --no-verify -F - <<'EOF'
  {{COMMIT_MESSAGE_BLOCK}}
  EOF

COMMIT_HASH = RUN git rev-parse --short HEAD
```

## Output

Return only:
```text
Commit stored: hash={{COMMIT_HASH}}, kind={{COMMIT_KIND}}, workflow={{COMMIT_WORKFLOW_KIND}}, empty={{EMPTY_COMMIT_USED}}, amended={{AMENDED}}
```
"""
