# Template Instruction Audit

Comprehensive audit of all 30 templates (7 commands + 23 agents) for weak, ambiguous, or unenforceable instructions that allow agents to deviate from intended behavior.

## The Problem

Agents interpret soft language loosely. When templates say "should", "consider", "proceed to", or "recommended", agents treat these as suggestions — substituting their own judgment, adding unauthorized outputs, or stopping workflows early.

Observed failure patterns:

1. **Unauthorized user interaction**: Agent asks the user for confirmation when MCP decision is "refine" (should auto-continue)
2. **Premature workflow termination**: Agent treats intermediate output (roadmap) as final output, never extracting phases
3. **Unauthorized file creation**: Agent writes `roadmap.md` despite roadmap being MCP-internal only
4. **Decision override**: Agent sees score is "close enough" and skips the MCP decision workflow entirely
5. **Scope creep in output**: Agent returns full document content when it should return only a status

## The Solution Style

Use emphatic, machine-readable enforcement blocks with explicit VIOLATION callouts. This format leaves no room for interpretation:

```text
═══════════════════════════════════════════════
MANDATORY [PROTOCOL NAME]
═══════════════════════════════════════════════
[Concise description of what MUST happen]

"value_a" → [Exact action]. Do NOT [common deviation].
"value_b" → [Exact action]. Do NOT [common deviation].

VIOLATION: [Specific agent behavior] when [condition]
           is a workflow violation. [Why it's wrong].
═══════════════════════════════════════════════
```

Key principles:

- Replace "should/may/can/consider" with "MUST/DO NOT/VIOLATION"
- State both what to DO and what NOT to do
- Name the specific deviation as a VIOLATION
- Use `═══` separator blocks for mandatory protocols
- Mark non-optional steps with `(MANDATORY)` in headers

## Batch Plan

Work through workflows one at a time:

| Batch | Workflow | Files | Status |
| ----- | -------- | ----- | ------ |
| 1 | Roadmap (command + agents) | roadmap_command.py, plan_command.py Step 10, roadmap.py, create_phase.py | In Progress |
| 2 | Plan (command + agents) | plan_command.py, plan_analyst.py, analyst_critic.py, plan_critic.py | Pending |
| 3 | Phase (command + agents) | phase_command.py, phase_architect.py, phase_critic.py | Pending |
| 4 | Task (command + agents) | task_command.py, task_planner.py, task_plan_critic.py, task_critic.py | Pending |
| 5 | Code (command + agents) | code_command.py, coder.py, code_reviewer.py, review team agents | Pending |
| 6 | Patch (command + agents) | patch_command.py, patch_planner.py | Pending |
| 7 | Cross-cutting patterns | TOOL INVOCATION sections, output scope restrictions, MCP tool naming | Pending |

## Command Template Findings

### plan_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 320-325 | Document structure constraints listed but no explicit consequence for violation | Missing gate | Agent adds extra H2 sections causing silent data loss |
| 337-339 | "Store in variable as CURRENT_PLAN" — no MUST enforcement | Soft language | Agent could skip MCP storage |
| 419-435 | User decision processing uses "IF user provides feedback along with their choice" | Ambiguous conditional | Agent might ignore feedback provided separately from choice |
| 467-480 | Fallback score for MCP decision not numerically specified | Vague recovery | Agent has discretion on what "fallback score" means |
| 617-627 | Step 10 doesn't prohibit writing roadmap files | Missing restriction | Agent writes roadmap.md on its own initiative |

### plan_conversation_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 79-92 | Conversational pacing is "Ask 1-2 questions" (suggested, not enforced) | Soft language | Agent asks 4-5 questions at once |
| 270-292 | Completion criteria uses "Ready to Complete When" (not "MUST complete when") | Soft enforcement | Agent declares conversation complete at 70% checklist |
| 187-211 | Technology search labeled "Active Search" but is conditionally triggered | Ambiguous trigger | Agent skips search if user seems knowledgeable |

### roadmap_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 183-186 | "complete" branch says "Proceed to Step 5" softly | Weak transition | Agent treats roadmap as final output, never extracts phases |
| 189-216 | Steps 5-6 not marked as MANDATORY | Missing enforcement | Agent skips phase extraction entirely |
| No line | No prohibition against writing roadmap files | Missing restriction | Agent writes roadmap.md to disk |
| 61-70 | Missing constraint sections triggers warning but proceeds | Non-blocking warning | Agent produces underspecified roadmap |
| 291 | No gate on what happens if 0 phases verify | Missing gate | Agent declares success with no phases |

### code_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 162-175 | Frontend mode detection based on incomplete keyword list | Incomplete detection | Misses "HTMX template" or misclassifies "component database" |
| 378-396 | Standards loop has no iteration limit | Missing limit | Agent loops forever if standards reviewer keeps finding issues |
| 199-201 | Config file reading has no error path if read fails | Missing error path | Agent concatenates empty strings |

### phase_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 320 | Decomposition detection relies on exact string "DECOMPOSITION_REQUIRED" | Fragile detection | Misses synonymous feedback like "Phase is oversized" |
| 424 | bp-pipeline failures are non-blocking | Missing gate | Invalid research paths proceed downstream |
| 260-263 | Phase status transition uses "should" not "MUST" | Soft language | Agent decomposes without updating status |

### task_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 223-224 | User can override MCP decision ("Override MCP decision and proceed") | Protocol violation | Contradicts MANDATORY DECISION PROTOCOL in other commands |
| 250 | TASK_NAME replacement assumes "phase-" prefix exists | Silent failure | Replacement fails if phase named "authentication" |
| 98-109 | Research extraction has no fallback if section doesn't exist | Missing fallback | Agent doesn't know whether to proceed or warn |

### patch_command.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 30-49 | Plan resolution uses loose heuristic ("references an active plan") | Ambiguous matching | Agent misinterprets normal text as plan reference |
| 74-96 | Phase discovery uses subjective "strongly relevant" | Subjective logic | Agent's relevance ranking is undocumented |
| 121 | Planning loop initialization has no error handling | Missing error path | Agent proceeds without checking if loop initialized |
| 255-273 | "DO NOT confuse" dual loop IDs — warning without enforcement | Warning only | Agent reuses wrong loop ID |

## Agent Template Findings

### roadmap.py (CRITICAL)

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 127-134 | File restriction says "File storage is handled exclusively by you" — contradicts "do NOT create files" | Contradictory | Agent sees both statements |
| 64-73 | TOOL INVOCATION section uses `{tools.*}` but agent doesn't see resolved tool names | Unclear tool names | Agent could hallucinate tool names |

### create_phase.py (CRITICAL)

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 115-127 | Output format says "Generate creation confirmation" but no explicit "DO NOT return phase markdown" | Weak output scope | Agent returns full phase content |

### coder.py (CRITICAL)

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 1-71 | No standard TOOL INVOCATION section | Missing section | Agent hallucinate tool call syntax |
| 40 | Filesystem boundary stated late and uses passive construction | Late/weak restriction | Agent uses shell commands instead of proper tools |

### plan_analyst.py (CRITICAL)

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 23-27 | No instruction on what to do if previous analysis exists | Missing refinement path | Agent creates fresh analysis every iteration instead of building on feedback |

### analyst_critic.py (CRITICAL)

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 120-127 | Verification checks listed but no instruction on what to DO if they fail | Missing consequence | Agent notes missing items but scores as acceptable |

### phase_architect.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 180-224 | Three sources for constraints with no priority order | Ambiguous priority | Agent may contradict plan decisions |
| 256-260 | Rejected technology handling says "note why it was rejected instead" | Too flexible | Agent could rationalize including rejected tech |

### phase_critic.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 183-209 | Post-synthesis validation mode doesn't specify feedback format changes | Missing mode spec | Agent generates full assessment in post_synthesis mode |
| 294-372 | Research path validation uses pseudocode regex, not executable instructions | Fragile parsing | Agent implements incorrectly |

### task_planner.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 173-185 | Research citation format inconsistent between description and example | Ambiguous format | Non-standard citations in output |

### task_critic.py

| Lines | Issue | Category | Impact |
| ----- | ----- | -------- | ------ |
| 114-129 | Deviation classification uses subjective categories ("Adds clarity") | Subjective scoring | Inconsistent quality assessment |

### Cross-cutting: Missing TOOL INVOCATION sections

These agents lack the standard TOOL INVOCATION block:

- plan_analyst.py
- analyst_critic.py
- task_planner.py
- patch_planner.py

### Cross-cutting: Inconsistent feedback storage

Some critics store feedback to MCP, others return to orchestrator:

- plan_critic.py: returns to Main Agent (human-driven)
- phase_critic.py: stores via MCP tool
- code_reviewer.py: stores via MCP tool

This is intentional (plan quality loop is human-driven) but not documented clearly enough for agents to understand why they behave differently.
