# specter-spec Command Specification

## Overview

The `/specter-spec` command transforms strategic plans into comprehensive technical specifications through an automated refinement loop with quality assessment and iterative improvement.

## Command Purpose

**Input**: Project name, specification phase name, optional technical focus
**Output**: Comprehensive technical specification meeting quality threshold (≥85%)
**Process**: Idempotent refinement loop with automated quality assessment

## Trigger Format

```text
/specter-spec <project_name> <spec_name> [focus]
```

**Parameters**:
- `project_name`: User-friendly Project name (system treats this as project_name)
- `spec_name`: Specification phase name (e.g., "Phase 1: Core API")
- `focus`: Optional technical area emphasis (e.g., "API design", "data architecture")

**Examples**:
```bash
/specter-spec best-practices-graph "Phase 1: Core API"
/specter-spec best-practices-graph "Phase 1: Core API" "API design"
/specter-spec analytics-platform "Phase 2: Data Pipeline" "scalability"
```

## Architecture Principles

### 1. Unified Specification Model

**TechnicalSpec Model** (replaces separate InitialSpec + TechnicalSpec):
- **iteration=0**: Sparse spec from roadmap (phase_name, objectives, scope, dependencies, deliverables)
- **iteration 1+**: Complete spec with all technical sections filled
- **Auto-versioning**: Each store operation increments iteration and version

### 2. Idempotent Agents

**spec-architect**:
- Retrieves current spec via MCP
- Generates or improves specification
- Stores updated spec via MCP
- Can be called multiple times with same loop_id safely

**spec-critic**:
- Retrieves spec via MCP
- Evaluates against FSDD criteria
- Stores feedback via MCP
- Idempotent evaluation

### 3. Self-Sufficient Agents

- Agents retrieve their own data from MCP (no markdown passing)
- Main Agent coordinates via loop_id only
- All state in MCP, agents are stateless functions

## Complete Workflow (9 Steps)

### Phase 1: Initialization (Steps 1-3)

#### Step 1: Initialize Refinement Loop
**Actor**: Main Agent
**MCP Call**: `mcp__specter__initialize_refinement_loop('spec')`
**Output**: `loop_id` for tracking this refinement session

#### Step 2: Retrieve Sparse Spec from Roadmap
**Actor**: Main Agent
**MCP Call**: `mcp__specter__get_spec(project_name, spec_name)`
**Output**: TechnicalSpec with iteration=0 (sparse template from roadmap)

**Sparse Spec Contents**:
- phase_name, objectives, scope, dependencies, deliverables
- All technical fields (architecture, technology_stack, etc.) are None

#### Step 3: Store Initial Spec in Loop
**Actor**: Main Agent
**MCP Call**: `mcp__specter__store_technical_spec(loop_id, spec_markdown)`
**Purpose**: Establish iteration=0 baseline for architect to retrieve

---

### Phase 2: Refinement Loop (Steps 4-7)

#### Step 4: Invoke spec-architect
**Actor**: Main Agent
**Action**: `Task(agent='specter-spec-architect', prompt with loop_id and focus)`

**spec-architect Workflow** (Idempotent):
1. Retrieve current spec: `mcp__specter__get_technical_spec_markdown(loop_id)`
2. Check iteration:
   - If 0: Generate complete spec from sparse template
   - If >0: Retrieve feedback and improve existing spec
3. If iteration>0: `mcp__specter__get_feedback_history(loop_id, count=3)`
4. Execute archive scanning for technical patterns
5. Generate/improve TechnicalSpec markdown
6. Store: `mcp__specter__store_technical_spec(loop_id, updated_spec)`
   - Auto-increments iteration and version
7. Return completion message

**Key Design**: Agent retrieves and stores via MCP. Main Agent only passes loop_id.

#### Step 5: Invoke spec-critic
**Actor**: Main Agent
**Action**: `Task(agent='specter-spec-critic', prompt with loop_id)`

**spec-critic Workflow** (Idempotent):
1. Retrieve spec: `mcp__specter__get_technical_spec_markdown(loop_id)`
2. Retrieve feedback history: `mcp__specter__get_feedback_history(loop_id, count=3)`
3. Evaluate against FSDD criteria (10 quality gates)
4. Generate feedback markdown with `overall_score` (0-100)
5. Store: `mcp__specter__store_critic_feedback(loop_id, feedback_markdown)`
6. Return completion message

**Key Design**: Critic retrieves and stores via MCP. Main Agent only passes loop_id.

#### Step 6: Get Loop Status
**Actor**: Main Agent
**MCP Call**: `mcp__specter__get_loop_status(loop_id)`
**Output**: `current_score` (latest quality score), `iteration_count`

#### Step 7: Decision Engine
**Actor**: Main Agent
**MCP Call**: `mcp__specter__decide_loop_next_action(loop_id, current_score)`

**Decision Logic**:
- **score ≥ 85**: Return `"complete"` → proceed to Step 8
- **score < 85 AND improvement ≥ 5**: Return `"refine"` → loop back to Step 4
- **score < 85 AND improvement < 5**: Return `"user_input"` → pause for guidance
- **iterations ≥ max (5)**: Return `"max_iterations"` → proceed to Step 8

**If "refine"**: Loop back to Step 4 (idempotent - architect retrieves updated state)
**If "user_input"**: Present feedback to user, get guidance, resume
**If "complete" or "max_iterations"**: Proceed to Step 8

---

### Phase 3: Completion (Steps 8-9)

#### Step 8: Finalize Specification
**Actor**: Main Agent
**MCP Call**: `mcp__specter__get_technical_spec_markdown(loop_id)`
**Output**: Complete TechnicalSpec markdown for platform storage

#### Step 9: Platform Storage
**Actor**: Main Agent
**Actions**:
1. Update roadmap: `mcp__specter__update_spec(project_name, spec_name, status='APPROVED')`
2. Store to platform: Use platform-specific tool (Linear/GitHub/Markdown)
3. Return completion message to user

**Completion Message Includes**:
- Final quality score
- Total iterations
- Platform storage location
- Next step recommendation (`/specter-build`)

---

## Data Flow Diagram

```text
User: /specter-spec project "Phase 1"
  ↓
┌─── Phase 1: Initialization ────┐
│ Main Agent:                    │
│  1. initialize_loop → loop_id  │
│  2. get_spec → sparse spec     │
│  3. store_spec(loop_id)        │
└────────────────────────────────┘
  ↓
┌──────────── Phase 2: Refinement Loop ────────────┐
│                                                  │
│  Main Agent: Invoke architect(loop_id, focus)    │
│    ↓                                             │
│  spec-architect (Self-Sufficient):               │
│    • get_technical_spec_markdown(loop_id)        │
│    • Generate/improve spec                       │
│    • store_technical_spec(loop_id, spec)         │
│    ↓                                             │
│  Main Agent: Invoke critic(loop_id)              │
│    ↓                                             │
│  spec-critic (Self-Sufficient):                  │
│    • get_technical_spec_markdown(loop_id)        │
│    • get_feedback_history(loop_id)               │
│    • Evaluate spec                               │
│    • store_critic_feedback(loop_id, feedback)    │
│    ↓                                             │
│  Main Agent:                                     │
│    • get_loop_status(loop_id)                    │
│    • decide_loop_next_action(loop_id, score)     │
│    ↓                                             │
│  Decision: refine? → Loop back to architect      │
│            complete? → Exit to Phase 3           │
└──────────────────────────────────────────────────┘
  ↓
┌─── Phase 3: Completion ─────┐
│ Main Agent:                 │
│  8. get_technical_spec      │
│  9. Store to platform       │
└─────────────────────────────┘
  ↓
User: "Spec complete! Score: 88%, Platform: Linear #123"
```

## MCP Tools Used

### Loop Management
- `initialize_refinement_loop(loop_type='spec')` - Create refinement session
- `get_loop_status(loop_id)` - Get current score and iteration count
- `decide_loop_next_action(loop_id, current_score)` - Determine next step

### Specification Operations
- `get_spec(project_name, spec_name)` - Retrieve sparse spec from roadmap
- `store_technical_spec(loop_id, spec_markdown)` - Store with auto-versioning
- `get_technical_spec_markdown(loop_id)` - Retrieve current spec state
- `update_spec(project_name, spec_name, status)` - Update roadmap status

### Feedback Operations
- `get_feedback_history(loop_id, count)` - Retrieve recent critic feedback
- `store_critic_feedback(loop_id, feedback_markdown)` - Store evaluation

### Roadmap Operations
- `get_project_plan_markdown(project_name)` - Retrieve strategic context (used by architect internally)

## Quality Gates

### FSDD Assessment Criteria (10 Gates)

The spec-critic evaluates specifications against:

1. **Technical Completeness** - All components specified
2. **Architecture Clarity** - Design decisions documented
3. **Integration Points** - External systems identified
4. **Data Models** - Structure and relationships defined
5. **Security Design** - Security considerations addressed
6. **Performance Targets** - Metrics and benchmarks specified
7. **Scalability Plan** - Growth patterns considered
8. **Testing Strategy** - Validation approach defined
9. **Deployment Architecture** - Infrastructure specified
10. **Monitoring Plan** - Observability defined

### Success Criteria

- **Quality Threshold**: 85% (configurable via `FSDD_LOOP_SPEC_THRESHOLD`)
- **Maximum Iterations**: 5 (configurable via `FSDD_LOOP_SPEC_MAX_ITERATIONS`)
- **Improvement Threshold**: 5 points minimum between iterations

## Key Design Benefits

### 1. Idempotency
- **Safe Retries**: Can retry any step with same loop_id without corruption
- **Crash Recovery**: Agents always retrieve latest state from MCP
- **No Side Effects**: All state in MCP, agents are pure functions

**Example**:
```bash
# Call 1: Architect generates spec, stores at iteration=1
/specter-spec project "Phase 1"

# Architect crashes during evaluation
# Call 2: Retry with same loop_id
# Architect retrieves iteration=1, improves to iteration=2
# No data corruption, clean continuation
```

### 2. Simplicity
- **9 steps vs 20**: Much easier to understand and debug
- **One model**: No confusion about InitialSpec vs TechnicalSpec
- **Clear handshakes**: loop_id is the only coordination needed

### 3. State Visibility
- **Check any point**: `get_technical_spec_markdown(loop_id)` shows current state
- **Version history**: iteration and version track every change
- **Audit trail**: Feedback history shows all evaluations

### 4. Agent Autonomy
- **Self-sufficient**: Agents retrieve their own data
- **No coupling**: Main Agent doesn't need to know spec structure
- **Easy testing**: Idempotent agents are trivial to unit test

## Environment Variables

- `FSDD_LOOP_SPEC_THRESHOLD`: Quality score threshold (default: 85)
- `FSDD_LOOP_SPEC_MAX_ITERATIONS`: Maximum refinement iterations (default: 5)
- `FSDD_LOOP_SPEC_MIN_IMPROVEMENT`: Minimum improvement per iteration (default: 5)

## Error Handling

### Spec Not Found
```bash
/specter-spec project "NonExistent Phase"
# Error: No specification template found for "NonExistent Phase"
# Available specs: Phase 1: Core API (DRAFT), Phase 2: Integration (DRAFT)
```

### Loop Stagnation
- If improvement < 5 points between iterations
- System prompts user for additional guidance
- User can provide focus area or accept current spec

### Maximum Iterations Reached
- System completes workflow with current spec
- Presents final score and feedback
- User can manually trigger additional refinement if needed

## Success Metrics

### Quantitative
- **Quality Score**: Target ≥85%
- **Iteration Count**: Average 2-3 iterations per spec
- **Time to Complete**: ~5-15 minutes depending on complexity

### Qualitative
- **Specification Completeness**: All FSDD gates addressed
- **Implementation Readiness**: Sufficient detail for development
- **Research Requirements**: Knowledge gaps identified

## Platform Integration

### Linear
- Spec stored as Linear issue with custom fields
- Labels: `spec`, `phase-1`, `approved`
- Status: `Approved Specification`

### GitHub
- Spec stored as markdown in `/docs/specs/` directory
- Automatically committed with message including score
- PR created for team review

### Markdown Files
- Spec stored in project directory
- Filename: `{project_name}-{spec_name}.md`
- Includes metadata header with score and iteration count

## Related Documentation

- [SPECTER_SPEC_WORKFLOW_OPTIMIZATION.md](../implementation/SPECTER_SPEC_WORKFLOW_OPTIMIZATION.md) - Complete workflow architecture
- [spec-architect.md](../agents/spec-architect.md) - Architect agent specification
- [spec-critic.md](../agents/spec-critic.md) - Critic agent specification
- [specter-spec-integration-test.md](../testing/specter-spec-integration-test.md) - Integration tests

## Next Steps

After completing the specification phase:
1. Review the approved specification
2. Create implementation tasks: `/specter-build <project_name> <spec_name>`
3. Begin development following the technical specification
