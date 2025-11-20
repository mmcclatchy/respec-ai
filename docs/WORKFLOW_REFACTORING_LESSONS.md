# Workflow Refactoring Lessons: System-Wide Patterns

## Executive Summary

This document captures essential lessons learned from refactoring the spec workflow tools and storage architecture. These patterns apply broadly across all workflows (roadmap, plan, build, spec) and provide actionable guidance for identifying inefficiencies, reducing technical debt, and maintaining clean architecture.

**Key Achievement**: Consolidated spec tools from 11 to 6 (45% reduction) while improving idempotency, reducing token usage, and eliminating storage duplication.

## Core Refactoring Principles

### 1. Single Source of Truth Principle

**Problem Pattern**: Multiple storage locations for the same entity at different lifecycle stages.

**Example from Spec Workflow**:
```python
# BEFORE (Anti-Pattern)
self._initial_specs: dict[str, dict[str, InitialSpec]] = {}      # Sparse specs
self._technical_specs: dict[str, dict[str, TechnicalSpec]] = {}  # Complete specs
```

**Root Cause**:
- Treating document states as separate entities
- Confusing lifecycle stages with data types
- Lack of state management fields

**Solution**:
```python
# AFTER (Best Practice)
self._specs: dict[str, dict[str, TechnicalSpec]] = {}  # Single source
# State managed via fields: iteration=0 (sparse) vs iteration>0 (complete)
```

**How to Identify**:
- Search for storage pattern: `_draft_X`, `_initial_X`, `_final_X`, `_X_v1`, `_X_v2`
- Multiple dictionaries storing "versions" of same concept
- Separate models for lifecycle stages (InitialSpec vs TechnicalSpec)
- Synchronization logic between storages

**Refactoring Checklist**:
- [ ] Consolidate into single storage dictionary
- [ ] Add state fields (`iteration`, `version`, `status`) to model
- [ ] Use optional fields for progressive population
- [ ] Remove synchronization/copying logic
- [ ] Update all access patterns to single source

**Benefits**:
- Eliminates sync bugs
- Reduces memory footprint
- Simplifies state management
- Single query point for data

---

### 2. Context Token Optimization

**Problem Pattern**: Overlapping MCP tool operations consuming excessive context tokens.

**Example from Spec Workflow**:
```text
BEFORE: 11 tools
├── roadmap_tools: add_spec, get_spec, update_spec, list_specs, delete_spec (5)
├── spec_tools: store_technical_spec, get_technical_spec_markdown, list_technical_specs, delete_technical_spec (4)
└── roadmap core: create_roadmap, get_roadmap (2)
```

**Root Cause**:
- Tool proliferation without consolidation review
- Duplicate operations for different "types" (initial vs technical)
- Missing dual-mode retrieval patterns
- Separate tools for similar operations

**Solution**:
```text
AFTER: 6 tools (45% reduction)
├── Roadmap: create_roadmap, get_roadmap (2)
└── Unified Spec: store_spec, get_spec_markdown, list_specs, delete_spec, link_loop_to_spec, unlink_loop (6)

get_spec_markdown accepts: (project_name, spec_name) OR (loop_id) - dual mode
```

**How to Identify**:
- Count MCP tools per workflow: `grep -r "@mcp.tool()" services/mcp/tools/`
- Look for operation pairs: `create_X` + `update_X` (can be unified to `store_X`)
- Find type-specific duplicates: `get_initial_X` + `get_technical_X`
- Check for retrieval-by-ID duplication

**Consolidation Patterns**:
1. **Upsert Semantics**: `add_X` + `update_X` → `store_X` (checks existence internally)
2. **Dual-Mode Retrieval**: Accept multiple identifier types (project_name+name OR loop_id)
3. **Optional Parameters**: Use optional fields instead of separate tools
4. **Lifecycle Management**: Use dedicated link/unlink tools for temp mappings

**Refactoring Checklist**:
- [ ] List all tools in workflow module
- [ ] Group by operation type (CRUD)
- [ ] Identify upsert opportunities
- [ ] Add dual-mode parameters where beneficial
- [ ] Measure token savings (tools × schema size)

**Token Impact Formula**:
```text
Token Savings = (Removed Tools × Average Tool Schema Size)
Spec Workflow: (11 - 6) × ~200 tokens = ~1000 tokens saved per request
```

---

### 3. Idempotent Agent Pattern

**Problem Pattern**: Agents receiving data as parameters, making retries unsafe and coupling command logic to agent implementation.

**Example from Original Design**:
```text
BEFORE (Anti-Pattern):
Command orchestrator:
  1. Retrieve spec markdown from MCP
  2. Pass markdown content to agent as parameter
  3. Agent processes and returns updated markdown
  4. Command stores updated markdown back to MCP

Agent invocation:
  Task agent=spec-architect spec_content="<entire spec markdown here>"

Problems:
- Retry: If agent crashes, command must reconstruct exact markdown state
- Coupling: Command must format agent inputs, agent has no autonomy
- Not idempotent: Re-running with same parameters may produce different results
```

**Root Cause**:
- Treating agents as pure functions (input → output)
- Command orchestrator manages state retrieval/storage
- Agents have no direct MCP access
- Retry requires state reconstruction from command context

**Solution - Idempotent Self-Sufficiency**:
```text
AFTER (Best Practice):
Command orchestrator:
  1. Pass only identifiers to agent
  2. Agent handles all MCP operations autonomously

Agent invocation:
  Task agent=spec-architect loop_id=abc123

Agent workflow (autonomous):
  1. Call mcp__specter__get_spec_markdown(loop_id=abc123)
  2. Process retrieved spec content
  3. Call mcp__specter__store_spec(project_name, spec_name, updated_markdown)

Benefits:
- Retry Safe: Agent always retrieves last successful state from MCP
- Decoupled: Command only passes identifiers, agent owns complete workflow
- Idempotent: Same loop_id always operates on same persisted state
```

**Idempotent Agent Contract**:
1. **Receive**: Identifiers only (`loop_id`, `project_name`), never data
2. **Retrieve**: Agent calls MCP tool to get current state (first operation)
3. **Process**: Agent performs its specialized work
4. **Store**: Agent calls MCP tool to save result (last operation)
5. **Return**: Agent returns completion message

**How to Identify Non-Idempotent Agents**:
- Agent parameters include `markdown`, `data`, `content`
- Command orchestrator calls `store_*` on behalf of agent
- Agent returns processed data to command for storage
- No MCP retrieval calls in agent tool permissions

**Refactoring Checklist**:
- [ ] Agent receives only identifiers
- [ ] Agent has `get_*_markdown` tool permission
- [ ] Agent has `store_*` tool permission
- [ ] Agent retrieves state as first operation
- [ ] Agent stores state as last operation
- [ ] Test: Can agent be called twice with same ID safely?

**Benefits**:
- Crash recovery: Retry from last successful state
- Debugging: Clear state at each step
- Testing: Mock MCP responses, test agent in isolation
- Decoupling: Agents independent of command logic

---

### 4. Temporary vs Permanent State Mapping

**Problem Pattern**: Needing both workflow-scoped (temporary) and domain-scoped (permanent) access to the same entities.

**Example from Spec Workflow**:
```text
Need: Access specs by loop_id during refinement (temporary workflow scope)
Also: Access specs by project_name + spec_name for permanent storage (domain scope)

Storage must support both access patterns simultaneously
```

**Solution - Dual-Layer State Architecture**:
```python
# Permanent Storage (Domain Entities)
self._specs: dict[str, dict[str, TechnicalSpec]] = {}
# Key: project_name -> spec_name -> TechnicalSpec
# Lifecycle: Persists beyond workflow sessions

# Temporary Mapping (Workflow Sessions)
self._loop_to_spec: dict[str, tuple[str, str]] = {}
# Key: loop_id -> (project_name, spec_name)
# Lifecycle: Created at workflow start, destroyed at completion
```

**Lifecycle Management**:
```python
# Workflow Start
link_loop_to_spec(loop_id="abc", project_name="proj1", spec_name="phase1")

# During Workflow
spec = get_spec_by_loop(loop_id="abc")  # Uses mapping to find permanent location

# Workflow Complete
unlink_loop(loop_id="abc")  # Cleanup temporary mapping
```

**How to Identify Need**:
- Workflows have loops that iterate on domain entities
- Same entity needs access by workflow ID and domain ID
- "Active session" concept separate from entity storage
- Need for cleanup when workflow completes

**Mapping Management Patterns**:
1. **Link on Entry**: Create mapping when workflow starts
2. **Access via Mapping**: Use loop_id throughout workflow
3. **Unlink on Exit**: Destroy mapping when workflow completes
4. **Permanent Remains**: Domain entity persists after mapping removed

**Refactoring Checklist**:
- [ ] Identify workflow-scope vs domain-scope access needs
- [ ] Create `_loop_to_entity` mapping dictionary
- [ ] Implement `link_loop_to_entity(loop_id, domain_keys...)`
- [ ] Implement `get_entity_by_loop(loop_id)` helper
- [ ] Implement `unlink_loop(loop_id)` cleanup
- [ ] Add cleanup to workflow completion step
- [ ] Test: Mapping created/destroyed at right times

**Anti-Patterns to Avoid**:
- Storing full entity copies in mapping (store keys only)
- Forgetting cleanup (abandoned mappings accumulate)
- Using mappings for permanent access (mappings are temporary)

---

### 5. API Breaking Change Management

**Problem Pattern**: Refactoring breaks tests, imports, documentation without clear detection.

**Lessons from Spec Consolidation**:

**What Broke**:
- 444 tests (caught all issues ✅)
- 7 documentation files (manual search required ⚠️)
- Tool discovery system (type checker caught ✅)
- Unused imports (linter caught ✅)

**Detection Tools**:
```bash
# 1. Type Checking (catches stale imports)
uv run mypy services/

# 2. Linting (catches unused imports)
uv run ruff check

# 3. Test Suite (catches API usage)
uv run pytest tests/ -v

# 4. Grep Search (catches doc references)
grep -r "old_function_name" docs/
```

**Systematic Change Process**:
1. **Make Code Changes**: Update implementation
2. **Run Tests**: Fix all test failures immediately
3. **Type Check**: Fix import/type errors
4. **Lint**: Remove unused imports
5. **Search Docs**: Find/update all documentation references
6. **Search Tests**: Verify test file cleanup
7. **Final Validation**: All checks pass

**Breaking Change Checklist**:
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Type check: `mypy services/`
- [ ] Lint check: `ruff check`
- [ ] Search for old names: `grep -r "old_name" .`
- [ ] Update documentation: `grep -r "old_name" docs/`
- [ ] Check tool discovery: `services/platform/tool_discovery.py`
- [ ] Verify imports: Search for old module names

**Documentation Debt Management**:
- Update docs **alongside** code changes (not after)
- Search patterns: `function_name`, `ClassName`, `old_tool_name`
- Check: Agent specs, command specs, architecture docs, user guide

---

### 6. State Evolution via Fields, Not Separate Models

**Problem Pattern**: Creating separate types/models for document lifecycle stages.

**Example from Spec Workflow**:
```python
# BEFORE (Anti-Pattern)
class InitialSpec(BaseModel):
    phase_name: str
    objectives: str
    scope: str
    dependencies: str
    deliverables: str
    # Technical fields absent

class TechnicalSpec(BaseModel):
    phase_name: str
    objectives: str
    scope: str
    dependencies: str
    deliverables: str
    architecture: str          # New fields
    technology_stack: dict
    data_models: dict
    # ... many more fields

# Result: Two models, duplication, conversion logic needed
```

**Root Cause**:
- Modeling lifecycle as type system
- Confusing "sparse" vs "complete" with "different types"
- Missing understanding of progressive state

**Solution - Progressive Field Population**:
```python
# AFTER (Best Practice)
class TechnicalSpec(BaseModel):
    # Always Required
    phase_name: str

    # Sparse State (iteration=0): Only these populated
    objectives: str
    scope: str
    dependencies: str
    deliverables: str

    # Complete State (iteration>0): These added progressively
    architecture: str | None = None
    technology_stack: dict | None = None
    data_models: dict | None = None
    # ... all technical fields optional

    # State Management
    iteration: int = 0  # 0=sparse, 1+=complete
    version: int = 1

# Create Alias for Clarity
InitialSpec = TechnicalSpec  # Same type, different semantic meaning
```

**State-Based Logic**:
```python
def process_spec(spec: TechnicalSpec):
    if spec.iteration == 0:
        # Sparse mode: Generate complete spec
        return generate_architecture(spec)
    else:
        # Complete mode: Refine existing spec
        return improve_architecture(spec)
```

**How to Identify**:
- Multiple models with `Initial*`, `Draft*`, `Final*` prefixes
- Models with 80%+ field overlap
- Conversion functions: `initial_to_technical()`, `draft_to_final()`
- Type checks on lifecycle: `isinstance(x, InitialSpec)`

**Refactoring Checklist**:
- [ ] Merge models into single type
- [ ] Make progressive fields optional (`field: Type | None = None`)
- [ ] Add state fields (`iteration`, `version`, `status`)
- [ ] Replace type checks with state checks (`if spec.iteration == 0`)
- [ ] Remove conversion functions
- [ ] Update storage to single type
- [ ] Create type aliases if helpful for semantics

**Benefits**:
- No conversion logic needed
- Single storage location
- Clear state progression
- Easier to extend with new fields

---

### 7. Test Cleanup Philosophy

**Problem Pattern**: Accumulating outdated/skipped tests that don't validate current functionality.

**Decision Framework**:
```text
Does test validate current functionality?
├─ YES → Update to new API
└─ NO → Does workflow exist?
    ├─ YES → Update to new API
    └─ NO → Delete test (don't skip)
```

**Example from Spec Consolidation**:
```python
# WRONG: Skipping tests
@pytest.mark.skip(reason="Needs update for unified spec tools API")
def test_old_workflow():
    # Old test that should be updated or deleted
    pass

# RIGHT: Delete obsolete tests
# If workflow changed and test no longer applicable → delete the test file
# If API changed but workflow same → update the test
```

**Test Aging Patterns**:
1. **Integration tests age faster** than unit tests (more dependencies)
2. **Workflow tests age fastest** (tied to orchestration logic)
3. **Unit tests age slowest** (isolated to single function)

**Refactoring Approach**:
```text
After API consolidation:
1. Run test suite → identify failures
2. For each failure:
   a. Does it test a current workflow? → Update
   b. Does it test deleted functionality? → Delete test
   c. Does it test future functionality? → Delete or move to future/ dir
3. Never skip tests "temporarily" (they become permanent)
```

**Test File Deletion Criteria**:
- Tests old API that no longer exists
- Tests workflow that isn't implemented
- No way to update without complete rewrite
- Duplicates coverage from other tests

**Keep vs Delete Examples**:
```text
DELETE: test_spec_tools_integration.py
Reason: Tests old store_technical_spec() API that doesn't exist

DELETE: test_roadmap_server_integration.py
Reason: Tests old add_spec() workflow replaced by store_spec()

UPDATE: test_state_manager.py
Reason: Core functionality unchanged, just API names changed

DELETE: specter-spec-integration-test.md
Reason: Test plan for unimplemented /specter-spec command
```

**Refactoring Checklist**:
- [ ] Run tests: `pytest tests/ -v`
- [ ] No skipped tests remaining
- [ ] Delete obsolete integration test files
- [ ] Update unit tests for API changes
- [ ] Test files match implemented features
- [ ] Remove future feature test plans (or move to design docs)

---

### 8. Tool Naming Consistency

**Problem Pattern**: Mixed naming conventions across MCP tool modules.

**Example of Inconsistency**:
```text
roadmap_tools: add_spec, update_spec, get_spec
spec_tools: store_technical_spec, get_technical_spec_markdown
plan_tools: create_plan, update_plan, retrieve_plan
```

**Root Cause**:
- Organic growth without naming guidelines
- Domain-specific language mixing with technical operations
- Lack of CRUD operation standardization

**Solution - Unified Naming Convention**:
```text
MCP Tool Naming Standard:

CRUD Operations:
- store_*       (upsert: create or update)
- get_*         (retrieve single entity)
- list_*        (retrieve multiple entities)
- delete_*      (remove entity)

Specialized Operations:
- link_*        (create temporary mapping)
- unlink_*      (remove temporary mapping)
- initialize_*  (start workflow)
- decide_*      (make workflow decision)

Suffixes:
- *_markdown    (returns markdown format)
- *_data        (returns structured data)
- *_status      (returns state information)
```

**Refactored Examples**:
```text
BEFORE: add_spec, update_spec, create_spec
AFTER:  store_spec (upsert handles both)

BEFORE: get_spec, retrieve_spec, fetch_spec
AFTER:  get_spec_markdown (clear format)

BEFORE: get_specs, list_all_specs, enumerate_specs
AFTER:  list_specs (standard list operation)
```

**Platform vs MCP Distinction**:
```text
Platform Tools (Linear/GitHub):
- create_issue, update_issue, get_issue, delete_issue
- Reason: Match platform API conventions

MCP Tools (Specter):
- store_spec, get_spec_markdown, list_specs, delete_spec
- Reason: Provide unified abstraction layer
```

**How to Audit Tool Names**:
```bash
# List all MCP tools
grep -r "@mcp.tool()" services/mcp/tools/ -A 1

# Check naming consistency
grep -r "def (add|create|update|store|get|retrieve|fetch|list|delete)" services/mcp/tools/
```

**Refactoring Checklist**:
- [ ] List all tools in module
- [ ] Group by operation type (CRUD)
- [ ] Standardize create/update → `store_*`
- [ ] Standardize retrieve → `get_*` or `get_*_markdown`
- [ ] Standardize enumerate → `list_*`
- [ ] Keep `delete_*` as-is (already standard)
- [ ] Update all callers
- [ ] Update documentation

---

## Systematic Workflow Review Process

Use this process to review any workflow (roadmap, plan, build, spec) for refactoring opportunities.

### Phase 1: Storage Layer Analysis

**File**: `services/utils/state_manager.py`

```python
# Check for duplicate storage
duplicates = [name for name in dir(state_manager) if name.startswith('_') and 'spec' in name.lower()]
# Example findings: _initial_specs, _technical_specs

# Check for proper state fields
model_fields = spec_model.__fields__.keys()
state_fields = ['iteration', 'version', 'status', 'created_at', 'updated_at']
has_state = any(f in model_fields for f in state_fields)
```

**Checklist**:
- [ ] No duplicate storage dictionaries for same entity
- [ ] State managed via fields, not separate storage
- [ ] Temporary mappings (`_loop_to_*`) have cleanup
- [ ] Backward compatibility aliases during transitions

### Phase 2: MCP Tools Analysis

**File**: `services/mcp/tools/*_tools.py`

```bash
# Count tools
tool_count=$(grep -c "@mcp.tool()" services/mcp/tools/spec_tools.py)

# Check for redundancy
grep "def (add|create|store|update)_" services/mcp/tools/spec_tools.py
```

**Checklist**:
- [ ] Tool count minimized (no redundant operations)
- [ ] Dual-mode retrieval where appropriate
- [ ] Consistent naming (store/get/list/delete)
- [ ] Each tool has single responsibility
- [ ] Upsert semantics where beneficial

### Phase 3: Agent Pattern Analysis

**Files**: `docs/agents/*-architect.md`, `docs/agents/*-critic.md`

**Checklist**:
- [ ] Agents receive only identifiers, not data
- [ ] Agents have `get_*_markdown` tool permission
- [ ] Agents have `store_*` tool permission
- [ ] Agents retrieve as first operation
- [ ] Agents store as last operation
- [ ] Retry-safe (idempotent)

### Phase 4: Data Model Analysis

**Files**: `services/models/*.py`

**Checklist**:
- [ ] State evolution via fields, not separate types
- [ ] Optional fields for progressive population
- [ ] Auto-versioning where needed
- [ ] No unnecessary type splits (Initial\* vs Technical\*)
- [ ] Type aliases for semantic clarity only

### Phase 5: Test Analysis

**Files**: `tests/**/*.py`

```bash
# Find skipped tests
grep -r "@pytest.mark.skip" tests/

# Find outdated integration tests
grep -r "old_function_name" tests/integration/
```

**Checklist**:
- [ ] All tests passing
- [ ] No skipped tests
- [ ] Integration tests updated or deleted
- [ ] Test files match implemented features
- [ ] Outdated test files removed

### Phase 6: Documentation Analysis

**Files**: `docs/**/*.md`

```bash
# Find references to old API
grep -r "old_tool_name" docs/

# Check consistency across docs
grep -r "store_spec\|add_spec\|update_spec" docs/
```

**Checklist**:
- [ ] Command docs reference current API
- [ ] Agent docs reflect idempotent pattern
- [ ] Architecture docs match implementation
- [ ] No references to deleted tools/methods

---

## Prioritized Refactoring Roadmap

Based on these lessons, review workflows in this order:

### 1. Build Workflow (High Priority)
**Files**: `build_plan_tools.py`, `docs/agents/build-*.md`

**Likely Issues**:
- Similar loop-based refinement pattern as spec
- May have duplicate storage for plan states
- Check for Initial vs Technical split

**Review Focus**:
- Storage duplication
- Agent idempotency
- Tool consolidation

### 2. Roadmap Workflow (Medium Priority)
**Files**: `roadmap_tools.py`, `docs/agents/roadmap-*.md`

**Likely Issues**:
- We removed 5 spec tools but didn't fully audit
- May have similar patterns in roadmap management

**Review Focus**:
- Tool count optimization
- Naming consistency

### 3. Plan Workflow (Medium Priority)
**Files**: `project_plan_tools.py`, `docs/agents/plan-*.md`

**Likely Issues**:
- Check for InitialPlan vs TechnicalPlan split
- Analyst/Critic pattern similar to spec

**Review Focus**:
- Model consolidation
- Agent idempotency

### 4. Loop Infrastructure (Low Priority - Foundational)
**Files**: `loop_tools.py`

**Review Focus**:
- Core infrastructure, affects all workflows
- Most critical but most stable
- Review last to avoid breaking dependencies

---

## Quick Reference: Refactoring Smells

### Red Flags to Search For

```bash
# Storage Duplication
grep -r "_initial_\|_draft_\|_final_" services/utils/

# Tool Redundancy
grep "@mcp.tool()" services/mcp/tools/*.py | wc -l

# Non-Idempotent Agents
grep -r "spec_markdown:\|data:\|content:" docs/agents/

# Type Splits
grep -r "class Initial.*:\|class Draft.*:\|class Final.*:" services/models/

# Skipped Tests
grep -r "@pytest.mark.skip" tests/

# Old API References
grep -r "add_spec\|update_spec\|get_technical_spec" docs/
```

### Green Patterns to Validate

```python
# ✅ Single Source of Truth
self._specs: dict[str, dict[str, TechnicalSpec]] = {}

# ✅ State via Fields
iteration: int = 0
version: int = 1

# ✅ Dual-Mode Retrieval
def get_spec_markdown(project_name: str | None, spec_name: str | None, loop_id: str | None)

# ✅ Idempotent Agent
tools:
  - mcp__specter__get_spec_markdown
  - mcp__specter__store_spec

# ✅ Upsert Semantics
def store_spec(...)  # handles create and update

# ✅ Temporary Mappings
self._loop_to_spec: dict[str, tuple[str, str]] = {}
```

---

## Conclusion

These eight principles form a comprehensive framework for maintaining clean, efficient workflow architecture:

1. **Single Source of Truth** - Eliminate storage duplication
2. **Token Optimization** - Consolidate overlapping tools
3. **Idempotent Agents** - Self-sufficient, retry-safe operations
4. **State Mapping** - Temporary workflow scope + permanent domain scope
5. **Breaking Changes** - Systematic detection and update process
6. **State Evolution** - Fields over types
7. **Test Cleanup** - Delete outdated, don't skip
8. **Naming Consistency** - Unified CRUD conventions

Apply these lessons systematically to each workflow using the review checklist. Prioritize high-traffic workflows (build, spec) before infrastructure (loop).

**Next Steps**: Use this document to review build_plan_tools.py and associated agents.
