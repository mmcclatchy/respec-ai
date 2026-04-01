# Template Instruction Audit

Comprehensive audit of all 30 templates (7 commands + 23 agents) for weak, ambiguous, or unenforceable instructions that allow agents to deviate from intended behavior.

## The Problem

Claude Code (Sonnet/Opus) follows these templates reasonably well even with soft language. Open-source models (Llama, Qwen, DeepSeek, Mistral) do not. They exploit every gap, interpret every "should" as optional, and default to their pretraining distribution when instructions are ambiguous.

This is not a capability problem — these models can follow strict instructions. It is an alignment training difference: Claude has heavy RLHF specifically on instruction adherence. Open-source models treat soft language as genuinely optional and default to "helpful assistant" behaviors (asking clarifying questions, adding extra context, writing files proactively) unless explicitly prohibited.

### Observed Failure Patterns

1. **Unauthorized user interaction**: Agent asks the user for confirmation when MCP decision is "refine" (MUST auto-continue)
2. **Premature workflow termination**: Agent treats intermediate output (roadmap) as final output, never extracting phases
3. **Unauthorized file creation**: Agent writes `roadmap.md` despite roadmap being MCP-internal only
4. **Decision override**: Agent sees score is "close enough" and skips the MCP decision workflow entirely
5. **Scope creep in output**: Agent returns full document content when it MUST return only a status
6. **Pretraining default bleed**: Agent reverts to generic "helpful assistant" patterns — asking questions, offering alternatives, adding commentary — when template doesn't exhaustively specify behavior

## Open-Source Model Behavior Differences

Understanding WHY open-source models drift differently from Claude is critical for writing effective templates.

### How Open-Source Models Process Instructions

| Behavior | Claude (Sonnet/Opus) | Open-Source Models |
| -------- | -------------------- | ------------------ |
| "should" / "consider" | Infers intent, usually complies | Takes the literal escape hatch |
| Prohibition ("DO NOT X") | Reliably avoids X | Sometimes treats as reminder that X exists, then does X |
| Long-range instruction memory | Strong — constraints from line 20 still active at line 400 | Weak — constraints decay with distance from point of action |
| System prompt vs user message | Both weighted equally | May deprioritize system prompt relative to user message |
| Competing instructions | Resolves toward most specific | Resolves toward most recent or most familiar pattern |
| Ambiguous gaps | Asks or does nothing | Fills with pretraining default (usually "be helpful") |
| Freeform vs structured output | Follows either | Much more reliable with structured templates to fill in |

### Key Insight

Open-source models don't ignore instructions — they exploit gaps. When the template doesn't exhaustively specify what to do at a given step, the model fills the gap with whatever its pretraining distribution suggests. For most models, that's "be a helpful assistant" — which means asking questions, writing extra files, offering alternatives, and adding commentary.

**The fix is not louder prohibitions. The fix is exhaustive positive instructions that leave no gap to fill.**

## The Solution Style

### Pattern 1: MANDATORY Enforcement Blocks (Prohibitions)

Use emphatic, machine-readable enforcement blocks with explicit VIOLATION callouts. This format works for behaviors that MUST NOT happen:

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

### Pattern 2: Exhaustive Positive Instructions (Gap Elimination)

More effective than prohibitions for open-source models. Specify exactly what to do at each step so completely that deviation requires actively ignoring the instruction, not just interpreting ambiguity:

```text
Step 4: Store roadmap via MCP
  1. Call create_roadmap with the full roadmap content.
  2. Capture the returned roadmap_id.
  3. Report: "Roadmap stored: {roadmap_id}"
  Your ONLY output for this step is the status line above.
```

This is better than:

```text
Step 4: Store roadmap via MCP
  Call create_roadmap. DO NOT write files. DO NOT ask the user.
  DO NOT return roadmap content. DO NOT add commentary.
```

The first version tells the model exactly what to do — no gap to fill. The second version lists prohibitions that open-source models may treat as a menu of options.

### Pattern 3: Inline Constraint Repetition

Open-source models have shorter effective instruction memory. Critical constraints MUST be restated at the point of action, not just in the preamble:

```text
# Top of template
MANDATORY: DO NOT write files to disk. All storage is via MCP tools only.

# ... 200 lines later, at the step where file writing actually happens ...
Step 7: Store phase document
  Call store_document with phase content.
  DO NOT write any files to disk. DO NOT create .md files.
  Your ONLY action is the MCP tool call above.
```

Redundancy that is noise for Claude is load-bearing for open-source models.

### Pattern 4: Structured Output Anchors

Open-source models are significantly more reliable when filling in a template than generating freeform output:

```text
Respond with EXACTLY this format, no other text:

STATUS: [complete|refine]
SCORE: [integer 0-100]
SUMMARY: [one sentence, max 20 words]
NEXT_ACTION: [exact tool call or "none"]
```

### Pattern 5: Positive-First, Prohibit-Second

Lead with what TO do. Follow with what NOT to do. Open-source models anchor on the first instruction they see for a given step:

```text
# Better — positive instruction first
Your ONLY output is: "Phase stored: {phase_id}, {phase_name}"
Do NOT return the phase markdown content.

# Worse — prohibition first (model sees "phase markdown content" and may produce it)
Do NOT return the phase markdown content.
Your ONLY output is: "Phase stored: {phase_id}, {phase_name}"
```

### Pattern 6: Decision Boundaries as Exhaustive Branches

Never leave a decision point with an implicit "else." Open-source models will invent behavior for unhandled cases:

```text
# Bad — implicit else
IF decision = "complete": execute Step 8
IF decision = "refine": execute Step 6

# Good — exhaustive branches, no gap
IF decision = "complete" → IMMEDIATELY execute Step 8. Do NOT execute any other step.
IF decision = "refine" → IMMEDIATELY execute Step 6. Do NOT execute any other step.
IF decision = any other value → STOP. Report error: "Unexpected decision: {value}"
```

## Application Principles

### Constraint Placement Strategy

1. **First 3 lines**: The single most important behavioral constraint (the one that fails most often)
2. **Last 3 lines**: The second most important constraint (recency bias)
3. **Inline at point of action**: Any constraint that governs a specific step — restate it there
4. **Preamble blocks**: General protocols that apply throughout

### Template Length Tradeoffs

More MANDATORY blocks = more total template length = more attention decay. The solution is NOT "make agents smaller" (that just shifts complexity to orchestration). Instead:

- **Extract shared protocol blocks into composable includes** — TOOL INVOCATION, DECISION PROTOCOL, OUTPUT SCOPE blocks that are near-identical across agents should be defined once and injected
- **Front-load the 2-3 constraints that actually fail** for each specific agent, rather than adding every possible prohibition
- **Use orchestrator-side validation** for critical gates — a 3-line check in the command template ("did agent return a file path?" → reject and retry) catches failures that prompt language cannot prevent

### The Prohibition Paradox

For open-source models, mentioning the wrong behavior can increase its probability. "DO NOT ask the user for confirmation" contains the concept "ask the user for confirmation" which the model may latch onto. Where possible, prefer exhaustive positive instructions that never mention the undesired behavior:

```text
# Risky for open-source models:
DO NOT ask the user for confirmation. DO NOT wait for user input.
Proceed directly to the next step.

# Safer:
Your ONLY action after receiving MCP decision "refine" is:
IMMEDIATELY execute Step 6 with the feedback content.
```

### Soft Language Replacement Guide

| Soft (remove) | Hard (replace with) |
| -------------- | ------------------- |
| should | MUST |
| consider | REQUIRED |
| recommended | MANDATORY |
| proceed to | IMMEDIATELY execute |
| you may want to | REQUIRED: |
| if appropriate | ALWAYS |
| try to | MUST |
| ideally | REQUIRED |
| optionally | (remove entirely, or make MANDATORY) |
| it would be good to | MUST |

## Batch Plan

Work through workflows one at a time. Each batch must re-audit with open-source model patterns in mind.

| Batch | Workflow | Files | Status |
| ----- | -------- | ----- | ------ |
| 1 | Roadmap (command + agents) | roadmap_command.py, plan_command.py Step 10, roadmap.py, create_phase.py | Pending |
| 2 | Plan + Roadmap (command + agents) | plan_command.py, plan_conversation_command.py, plan_critic.py, plan_analyst.py, analyst_critic.py, roadmap_command.py, roadmap.py, roadmap_critic.py | Complete |
| 3 | Phase (command + agents) | phase_command.py, phase_architect.py, phase_critic.py | Complete |
| 4 | Task (command + agents) | task_command.py, task_planner.py, task_plan_critic.py (task_critic.py removed — orphaned) | Complete |
| 5 | Code (command + agents) | code_command.py, coder.py, code_reviewer.py, review team agents | Pending |
| 6 | Patch (command + agents) | patch_command.py, patch_planner.py | Pending |
| 7 | Cross-cutting patterns | TOOL INVOCATION sections, output scope restrictions, MCP tool naming | Pending |

### Re-Audit Checklist (Apply to Every Template)

For each template in each batch, verify:

- [ ] **Gap audit**: Every step has exhaustive positive instructions (no implicit "else," no undefined behavior)
- [ ] **Soft language scan**: Zero instances of should/consider/recommended/proceed to/optionally
- [ ] **Constraint placement**: Top-failure constraints appear in first 3 lines AND inline at point of action
- [ ] **Output anchoring**: Every agent has a structured output format (not freeform)
- [ ] **Decision exhaustiveness**: Every IF/ELSE branch is explicit, including error cases
- [ ] **Prohibition paradox check**: Prohibitions don't inadvertently suggest the wrong behavior
- [ ] **Tool invocation section**: Present with resolved tool names (not `{tools.*}` placeholders)
- [ ] **Contradiction scan**: No two instructions in the same template that could be read as conflicting
- [ ] **Point-of-action repetition**: Critical constraints restated at the step where violation occurs

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
| 127-134 | File restriction says "File storage is handled exclusively by you" — contradicts "do NOT create files" | Contradictory | Agent sees both statements, open-source models pick whichever is most recent |
| 64-73 | TOOL INVOCATION section uses `{tools.*}` but agent doesn't see resolved tool names | Unclear tool names | Agent hallucinate tool names |

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

## Open-Source Model Testing Protocol

When applying fixes from this audit, validate against open-source models specifically. Claude compliance does not guarantee open-source compliance.

### Test Matrix

For each fixed template, run the same workflow on:

1. Claude Sonnet (baseline — should pass)
2. Primary open-source target model (the actual deployment model)
3. A weaker open-source model (stress test — if it works here, it works everywhere)

### Failure Signature Catalog

Track which failure patterns each model exhibits. This builds a model-specific knowledge base:

| Failure Pattern | Models Affected | Template Fix That Resolved It |
| --------------- | --------------- | ----------------------------- |
| (populate during re-audit) | | |

### Regression Indicators

A template fix is working if:

- The specific failure pattern stops occurring on the target model
- No new failure patterns emerge (prohibition paradox check)
- Claude compliance is not degraded (stronger instructions should not confuse Claude)
