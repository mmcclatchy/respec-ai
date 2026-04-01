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

## Phase Workflow Findings (Batch 2)

28 findings across phase_command.py, phase_architect.py, phase_critic.py, and create_phase.py. HIGH severity findings below.

### phase_command.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 260-263 | "should transition" soft language for decomposition status | HIGH | MANDATORY PHASE DECOMPOSITION PROTOCOL block |
| 423-425 | Non-blocking bp-pipeline error — agent continues with invalid research | HIGH | MANDATORY BP-PIPELINE VALIDATION GATE — workflow MUST stop |
| (implicit) | No prohibition on unauthorized file writes during phase storage | HIGH | MANDATORY PHASE FILE STORAGE RESTRICTION block |
| 308-314 | "Proceed to Step 8" soft transition on COMPLETE decision | MEDIUM | Strengthen with "IMMEDIATELY execute Step 8" |
| 313-314 | "phase-architect will retrieve feedback" soft enforcement | MEDIUM | Coordination issue with phase_architect STEP 0 |

### phase_architect.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 180-224 | Three constraint sources with conflicting priority — agent picks freely | HIGH | MANDATORY CONSTRAINT PRIORITY PROTOCOL — formal > strategic > ad-hoc |
| 238-260 | Plan context (architecture, tech decisions) stated as recommendations not bindings | HIGH | MANDATORY PLAN CONTEXT ENFORCEMENT — all plan decisions BINDING |
| 256-260 | Rejected tech loophole: "note why it was rejected instead" opens re-evaluation | HIGH | MANDATORY REJECTED TECHNOLOGY PROTOCOL — absolute prohibition |
| 88-100 | Feedback retrieval condition `iteration > 1` skips iteration 1 | HIGH | Fix to `iteration >= 1` with MANDATORY FEEDBACK RETRIEVAL PROTOCOL |
| 269-277 | "brief status message" without exact format specification | MEDIUM | MANDATORY STATUS MESSAGE FORMAT with exact fields |
| 82 | optional_instructions parameter documented but never referenced in workflow | MEDIUM | Add usage protocol |
| 765-779 | Idempotency claimed but not enforced | MEDIUM | Add MANDATORY IDEMPOTENCY PROTOCOL |

### phase_critic.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 177-209 | No enforcement on when to use full vs post_synthesis validation mode | HIGH | MANDATORY VALIDATION MODE SELECTION PROTOCOL |
| 183-209 | post_synthesis mode doesn't specify how to retrieve previous score | MEDIUM | Add explicit CALL instruction for score retrieval |
| 272-280 | Root cause classification thresholds are arbitrary with no justification | MEDIUM | Document thresholds as mandatory numeric rules |
| 466-475 | Custom H3 penalty deduction cap unclear for multiple violations | MEDIUM | Explicit max deduction = 5 points |
| 727-735 | Two BLOCKING penalties both cap at 80 — unclear if additive | MEDIUM | Single cap applies regardless of how many penalties |

### create_phase.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 115-125 | Output says "ONLY if both succeeded" then specifies "partial success" — contradiction | HIGH | MANDATORY CREATE PHASE OUTPUT PROTOCOL — 3 clear cases |
| 136-138 | Weak validation gate — "report rather than saving" but no STOP/EXIT | HIGH | MANDATORY PHASE COMPLETENESS VALIDATION GATE |
| 50-70 | Missing "DO NOT write files to disk" restriction | MEDIUM | MANDATORY PHASE EXTRACTION SCOPE RESTRICTION |

## Task Workflow Findings (Batch 3)

20 findings across task_command.py, task_planner.py, task_plan_critic.py, and task_critic.py.

### task_command.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 223-224 | User can override MCP decision — contradicts MANDATORY DECISION PROTOCOL | CRITICAL | MANDATORY USER INPUT PROTOCOL — user provides feedback only, MCP controls decision |
| 250 | Silent TASK_NAME replacement failure if phase lacks "phase-" prefix | HIGH | MANDATORY TASK NAME GENERATION PROTOCOL — error on unexpected format |
| 98-109 | Research extraction can't distinguish "section missing" from "section empty" | HIGH | MANDATORY RESEARCH EXTRACTION PROTOCOL |

### task_planner.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 91-112 | Constraint hierarchy uses soft language — "HARD CONSTRAINTS" in prose, not protocol block | MEDIUM | MANDATORY CONSTRAINT HIERARCHY block with VIOLATION callouts |
| 137-145 | Document structure constraints are descriptive warnings, not enforceable | MEDIUM | MANDATORY TASK DOCUMENT STRUCTURE with explicit prohibitions |
| 173-182 | Research citation format inconsistent between description and example | MEDIUM | Exact citation format specification |
| 1-130 | Missing TOOL INVOCATION section | HIGH | Add standard block |

### task_plan_critic.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 180-200 | Research citation validation uses passive "Verify/Check" language | HIGH | MANDATORY RESEARCH CITATION VALIDATION with explicit steps |
| 119-130 | change_description alignment findings have no reporting location | MEDIUM | Specify output location in Phase Alignment section |
| 270-303 | Score calibration uses subjective language ("adequate", "could be sharper") | MEDIUM | Explicit numeric scoring rules |
| 1-81 | Missing TOOL INVOCATION section | HIGH | Add standard block |

### task_critic.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 58 | Description says "Assess Phase quality" — should be "Task quality" | HIGH | Fix copy-paste error |
| 124-127 | Deviation classification uses subjective categories without objective rules | HIGH | MANDATORY DEVIATION CLASSIFICATION PROTOCOL with ALL/ANY criteria |
| 97-100 | Section validation uses passive warnings, "acceptable" contradicts strict policy | MEDIUM | MANDATORY SECTION VALIDATION block |
| 82-100 | No structural validation gate — unclear if violations prevent approval | HIGH | MANDATORY STRUCTURE VALIDATION GATE |
| 143-152 | Phase vocabulary ("features") mixed with Task vocabulary ("Steps") + typo | MEDIUM | Fix terminology |
| 1-81 | Missing TOOL INVOCATION section | HIGH | Add standard block |

## Code Workflow Findings (Batch 4)

23 findings across code_command.py, coder.py, code_reviewer.py, automated_quality_checker.py, spec_alignment_reviewer.py, review_consolidator.py, and coding_standards_reviewer.py.

### code_command.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 312-316 | Phase 1 coding loop has no iteration limit | HIGH | MANDATORY CODING LOOP LIMIT (max 8) |
| 378-396 | Phase 2 standards loop has no iteration limit | HIGH | MANDATORY STANDARDS LOOP LIMIT (max 5) |
| 318-322 | "Proceed to Step" soft language on COMPLETE decision | MEDIUM | "IMMEDIATELY execute" |

### coder.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 43-48 | TodoList gate has no VIOLATION callout | MEDIUM | MANDATORY TODOLIST GATE |
| 307-327 | Blocking issue resolution stated as bullets, not enforced | HIGH | MANDATORY BLOCKING ISSUE RESOLUTION |

### code_reviewer.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 126 | "Do NOT write files" is single-line constraint | HIGH | MANDATORY FILESYSTEM BOUNDARY RESTRICTION |
| 161-181 | Research context extraction has no fallback | HIGH | MANDATORY RESEARCH CONTEXT EXTRACTION |

### review_consolidator.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 160-162 | Blocking score cap stated as calculation, not enforced | HIGH | MANDATORY BLOCKING ISSUE SCORE CAP (hardcap 79) |

### spec_alignment_reviewer.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 107-136 | No output scope definition — no "DO NOT write to disk" | HIGH | MANDATORY OUTPUT SCOPE block |

### coding_standards_reviewer.py

| Lines | Issue | Severity | Fix |
| ----- | ----- | -------- | --- |
| 183 | Type hint deduction logic ambiguous — might double-count with mypy | MEDIUM | MANDATORY TYPE HINT DEDUCTION PROTOCOL |
