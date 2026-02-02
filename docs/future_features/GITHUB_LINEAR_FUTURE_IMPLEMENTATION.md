# GitHub and Linear Platform Implementation Plan

**Status:** 📋 Planned (Not Implemented)

**Target:** Post-MVP Feature

## Executive Summary

The GitHub and Linear platform adapters currently use **hypothetical/simplified** tool signatures that don't match the **actual** GitHub and Linear MCP server APIs. This document outlines the complete implementation plan for making these platforms fully functional.

**Current State:**
- ✅ **Markdown Platform:** Fully functional, 585 tests passing
- 🚧 **GitHub Platform:** Design mockup only - missing required parameters
- 🚧 **Linear Platform:** Design mockup only - incorrect parameter types

## Problem Statement

The adapters provide pseudo-code instructions that look like they would work, but cannot actually interact with real GitHub and Linear MCP servers due to:

1. **Missing required parameters** (GitHub needs `owner`, Linear needs `teamId`)
2. **Incorrect parameter types** (Linear uses `labels=[]` array, not `label=''` string)
3. **Unverified API assumptions** (Unknown if Linear `get_document()` exists)

## Critical Differences Found

### GitHub MCP Server (Real vs. Current)

**Real `create_milestone` signature:**
```python
mcp__github__create_milestone(
    owner="username",      # ❌ MISSING in our adapter
    repo="repo-name",      # ✅ We have this
    title="milestone",     # ✅ We have this
    state="open",          # Optional
    description="...",     # Optional
    due_on="2026-12-31"    # Optional
)
```

**Our current adapter:**
```python
# Just returns tool name: mcp__github__create_milestone
# Usage in templates assumes: (repo={PLAN_NAME}, title={PHASE_NAME})
# Missing: owner parameter!
```

**Impact:** All GitHub sync/discovery instructions missing `owner` parameter, making them non-functional.

### Linear MCP Server (Real vs. Current)

**Real `create_issue` signature:**
```python
mcp__linear__create_issue(
    title="Issue title",       # ✅ We have this
    description="...",         # Optional
    teamId="team-uuid",        # ❌ We use 'project' instead!
    assigneeId="user-uuid",    # Optional
    priority=0-4,              # Optional
    labels=["label-id"]        # ❌ We use label='phase' (string) instead of array!
)
```

**Our current adapter:**
```python
# Sync instructions use:
mcp__linear-server__get_issue(
    project={PLAN_NAME},       # ❌ Should be teamId!
    title={PHASE_NAME},
    label='phase'              # ❌ Should be labels=['phase-label-id']!
)
```

**Impact:** Linear adapter cannot actually call MCP tools due to wrong parameter names and types.

## Affected Files

### GitHub Adapter Issues

**File:** `src/platform/adapters/github.py`

All sync and discovery instructions need updates:

| Method | Issue | Required Fix |
|--------|-------|--------------|
| `plan_sync_instructions` | Missing `owner` in `get_file()` | Add owner parsing from PLAN_NAME |
| `phase_sync_instructions` | Missing `owner` in `get_milestone()` | Add owner parsing |
| `task_sync_instructions` | Missing `owner` in `get_issue()` | Add owner parsing |
| `phase_discovery_instructions` | Missing `owner` in `list_milestones()` | Add owner parsing |
| `task_discovery_instructions` | Missing `owner` in `list_issues()` | Add owner parsing |

### Linear Adapter Issues

**File:** `src/platform/adapters/linear.py`

All sync and discovery instructions use wrong parameters:

| Method | Current | Should Be |
|--------|---------|-----------|
| `plan_sync_instructions` | `project={PLAN_NAME}` | `teamId={LINEAR_TEAM_ID}` |
| `phase_sync_instructions` | `project=, label='phase'` | `teamId=, labels=[{PHASE_LABEL_ID}]` |
| `task_sync_instructions` | `project=, label='task'` | `teamId=, labels=[{TASK_LABEL_ID}]` |
| All discovery methods | `project=, label=''` | `teamId=, labels=[]` |

## Implementation Roadmap

### Phase 1: Research & Validation

**Goal:** Verify actual GitHub and Linear MCP tool APIs

**Tasks:**
1. ✅ Confirm GitHub tool signatures (done via web search)
2. ✅ Confirm Linear tool signatures (done via web search)
3. Verify Linear `get_document()` exists or determine alternative
4. Test label creation capabilities in Linear MCP
5. Document all actual tool signatures with sources

**Estimated Effort:** 1-2 days

### Phase 2: GitHub Adapter Implementation

**Goal:** Make GitHub adapter functional with real MCP server

**Assumption:** `PLAN_NAME` format is `"owner/repo"` (e.g., `"facebook/react"`)

**Changes Required:**

1. **Update all sync instructions** (~40 lines):
   ```python
   @property
   def phase_sync_instructions(self) -> str:
       return """
   OWNER, REPO = {PLAN_NAME}.split('/')
   TRY:
     PHASE_RESULT = mcp__github__get_milestone(
       owner=OWNER,
       repo=REPO,
       title={PHASE_NAME}
     )
     mcp__respec-ai__store_document(
       doc_type="phase",
       key=f"{PLAN_NAME}/{PHASE_NAME}",
       content=PHASE_RESULT.description
     )
     Display: "✓ Loaded phase '{PHASE_NAME}' from GitHub"
   EXCEPT:
     Display: "No existing phase found in GitHub"
   """
   ```

2. **Update all discovery instructions** (~30 lines)
3. **Update documentation properties** (~10 lines)
4. **Add CLI validation** for `owner/repo` format (~20 lines)

**Estimated Effort:** 2-3 days (including testing)

### Phase 3: Linear Adapter Implementation

**Goal:** Make Linear adapter functional with real MCP server

**Prerequisites:**
- Determine plan storage strategy (Project vs. Issue with label)
- Design config schema for Linear settings
- Implement label management in CLI

**Config Structure:**
```json
{
  "plan_name": "my-project",
  "platform": "linear",
  "linear": {
    "team_id": "team-uuid-here",
    "labels": {
      "plan": "label-uuid-1",
      "phase": "label-uuid-2",
      "task": "label-uuid-3"
    }
  }
}
```

**Changes Required:**

1. **Update config schema** (`src/models/config.py`, ~15 lines):
   ```python
   class LinearConfig(BaseModel):
       team_id: str
       labels: dict[str, str]

   class RespecConfig(BaseModel):
       plan_name: str
       platform: str
       linear: LinearConfig | None = None
   ```

2. **Update sync instructions** (~50 lines):
   ```python
   @property
   def phase_sync_instructions(self) -> str:
       return """TRY:
     PHASE_RESULT = mcp__linear__get_issue(
       teamId={LINEAR_TEAM_ID},
       title={PHASE_NAME},
       labels=[{LINEAR_PHASE_LABEL_ID}]
     )
     # ... rest of implementation
   """
   ```

3. **Update CLI init command** (~100 lines):
   - Prompt for team ID or auto-discover teams
   - Create labels if they don't exist
   - Store config with Linear settings

4. **Update template helpers** (~10 lines):
   - Interpolate `{LINEAR_TEAM_ID}` placeholder
   - Interpolate `{LINEAR_*_LABEL_ID}` placeholders

**Estimated Effort:** 3-4 days (including CLI enhancements)

### Phase 4: Testing

**Goal:** Ensure adapters generate correct instructions

**Unit Tests** (`tests/unit/platform/`):

```python
# test_github_adapter.py (~100 lines)
def test_phase_sync_instructions_includes_owner_parsing():
    adapter = GitHubAdapter()
    instructions = adapter.phase_sync_instructions

    assert "OWNER, REPO = {PLAN_NAME}.split('/')" in instructions
    assert "owner=OWNER" in instructions
    assert "repo=REPO" in instructions
    assert "mcp__github__get_milestone" in instructions

# test_linear_adapter.py (~50 lines)
def test_phase_sync_instructions_uses_team_id():
    adapter = LinearAdapter()
    instructions = adapter.phase_sync_instructions

    assert "teamId={LINEAR_TEAM_ID}" in instructions
    assert "labels=[{LINEAR_PHASE_LABEL_ID}]" in instructions
```

**Integration Tests** (optional, ~200 lines):
- Mock GitHub/Linear MCP server responses
- Test full command generation flow
- Verify template interpolation

**Estimated Effort:** 2 days

### Phase 5: Documentation

**Goal:** Comprehensive setup guides for each platform

**New Documentation Files:**

1. **`docs/GITHUB_SETUP.md`** (~100 lines):
   - Prerequisites (GitHub MCP server, PAT token)
   - PLAN_NAME format requirements (`owner/repo`)
   - Resource mapping (plan → file, phase → milestone, task → issue)
   - Example workflows

2. **`docs/LINEAR_SETUP.md`** (~100 lines):
   - Prerequisites (Linear MCP server, API key)
   - Team ID discovery process
   - Label setup (automatic vs. manual)
   - Config structure explanation
   - Resource mapping (all → issues with labels)

**Documentation Updates:**

1. **`docs/CLI_GUIDE.md`**:
   - Add platform-specific initialization examples
   - Document GitHub `--plan-name` format
   - Document Linear `--team-id` option
   - Add troubleshooting section

2. **`README.md`**:
   - Update platform comparison table:
     ```text
     | Platform | Status | Tested | Setup |
     |----------|--------|--------|-------|
     | Markdown | ✅ Working | ✅ 585 tests | Simple |
     | GitHub   | ✅ Beta | ⚠️ Manual | Medium |
     | Linear   | ✅ Beta | ⚠️ Manual | Complex |
     ```

**Estimated Effort:** 1-2 days

## Total Implementation Effort

**Conservative Estimate:** 10-15 days
- Phase 1 (Research): 1-2 days
- Phase 2 (GitHub): 2-3 days
- Phase 3 (Linear): 3-4 days
- Phase 4 (Testing): 2 days
- Phase 5 (Docs): 1-2 days
- Buffer for unknowns: 1-2 days

## Key Decisions Needed

Before implementation can begin, these questions must be resolved:

### 1. GitHub PLAN_NAME Format

**Question:** Should we use `"owner/repo"` convention or add separate config?

**Options:**
- A. Parse from PLAN_NAME (simpler, requires validation)
- B. Add `github_owner` to config (more explicit)
- C. Auto-detect from `gh` CLI (fragile)

**Recommendation:** Option A - convention over configuration

### 2. Linear Plan Storage

**Question:** How should strategic plans be stored in Linear?

**Options:**
- A. Linear Projects with description (if document API exists)
- B. Dedicated issue with label="plan"
- C. Team description field

**Recommendation:** Option B - consistent with phase/task pattern

### 3. Linear Team Discovery

**Question:** Should CLI auto-discover teams or require manual input?

**Options:**
- A. Auto-discover and prompt for selection (better UX)
- B. Require `--team-id` flag (simpler implementation)
- C. Support both methods

**Recommendation:** Option C - support both for flexibility

### 4. Breaking Changes Policy

**Question:** How to handle breaking changes to adapter APIs?

**Options:**
- A. Mark as experimental, accept breaking changes
- B. Version bump to 2.0.0
- C. Maintain backwards compatibility

**Recommendation:** Option A - still pre-1.0 mindset

## Risks and Mitigations

### Risk 1: No Access to Real MCP Servers

**Impact:** Cannot test actual API compatibility

**Mitigation:**
- Unit test instruction generation (testable without servers)
- Rely on documented API signatures from web research
- Community testing after release
- Mark platforms as "Beta" until verified

### Risk 2: Linear API Assumptions Invalid

**Impact:** May need to redesign Linear adapter if `get_document()` doesn't exist

**Mitigation:**
- Research Linear MCP tools before implementation
- Design fallback strategy (use issues for everything)
- Document limitations clearly

### Risk 3: Complex User Onboarding

**Impact:** Users may struggle with team IDs, label setup, config editing

**Mitigation:**
- Auto-discovery where possible
- Clear error messages with examples
- Comprehensive setup documentation
- Video walkthrough (optional)

### Risk 4: Maintenance Burden

**Impact:** Two additional platforms to maintain alongside Markdown

**Mitigation:**
- Shared base class minimizes duplicate code
- Adapter pattern isolates platform-specific logic
- Unit tests catch regressions
- Mark as community-maintained if needed

## Success Criteria

Implementation is complete when:

✅ GitHub adapter generates instructions with `owner` and `repo` parsing
✅ Linear adapter uses `teamId` instead of `project`
✅ Linear adapter uses `labels=[]` array instead of `label=''` string
✅ CLI validates GitHub plan name format (`owner/repo`)
✅ CLI prompts for Linear team ID or auto-discovers teams
✅ CLI creates Linear labels and stores IDs in config
✅ Config schema includes `linear` section
✅ Template helpers interpolate Linear placeholders
✅ Unit tests verify adapter instruction generation
✅ Documentation explains platform setup
✅ All tests pass (595+ tests expected)
✅ At least one community member successfully uses GitHub platform
✅ At least one community member successfully uses Linear platform

## Alternative Approaches Considered

### 1. Remove GitHub/Linear Adapters Entirely

**Pros:** Simpler codebase, no maintenance burden

**Cons:** Removes planned features, limits platform options

**Decision:** Rejected - adapter pattern is good architecture even if not all implemented

### 2. Implement Only GitHub (Skip Linear)

**Pros:** Less complexity, GitHub more common

**Cons:** Linear users left out, incomplete feature

**Decision:** Consider if implementation proves too complex

### 3. Create Separate Packages

**Pros:** `respec-ai-github`, `respec-ai-linear` as optional plugins

**Cons:** Increased packaging complexity, fragmented ecosystem

**Decision:** Rejected - monorepo approach preferred

## References

### GitHub MCP Server

- [GitHub MCP Server Repository](https://github.com/github/github-mcp-server)
- [Milestone CRUD PR #1032](https://github.com/github/github-mcp-server/pull/1032)
- [GitHub REST API - Milestones](https://docs.github.com/en/rest/issues/milestones)

### Linear MCP Server

- [Linear MCP Documentation](https://linear.app/docs/mcp)
- [Linear MCP Server Implementation](https://github.com/tacticlaunch/mcp-linear)
- [How to Set Up Linear MCP](https://apidog.com/blog/linear-mcp-server/)

## Appendix: Current Adapter Code Analysis

### GitHub Adapter Methods

**File:** `src/platform/adapters/github.py`

All methods that need updates:

```python
# Sync Instructions (3 methods × ~15 lines each = 45 lines)
plan_sync_instructions     # Add owner parsing
phase_sync_instructions    # Add owner parsing
task_sync_instructions     # Add owner parsing

# Discovery Instructions (2 methods × ~10 lines each = 20 lines)
phase_discovery_instructions  # Add owner parsing
task_discovery_instructions   # Add owner parsing

# Tool Properties (13 methods - return tool names only)
create_plan_tool          # No change needed
retrieve_plan_tool        # No change needed
update_plan_tool          # No change needed
create_phase_tool         # No change needed
retrieve_phase_tool       # No change needed
update_phase_tool         # No change needed
comment_phase_tool        # No change needed
create_task_tool          # No change needed
retrieve_task_tool        # No change needed
update_task_tool          # No change needed
list_phases_tool          # No change needed
list_tasks_tool           # No change needed
create_plan_completion_tool  # No change needed

# Documentation Properties (7 methods × ~2 lines each = 14 lines)
coding_standards_location
phase_location_hint
plan_discovery_instructions
task_discovery_instructions
plan_location_hint
task_location_hint
# ... etc
```

**Total Lines to Modify:** ~80 lines

### Linear Adapter Methods

**File:** `src/platform/adapters/linear.py`

All methods that need updates:

```python
# Sync Instructions (3 methods × ~15 lines each = 45 lines)
plan_sync_instructions     # Replace project= with teamId=
phase_sync_instructions    # Replace project= with teamId=, label= with labels=[]
task_sync_instructions     # Replace project= with teamId=, label= with labels=[]

# Discovery Instructions (3 methods × ~10 lines each = 30 lines)
plan_discovery_instructions   # Update if needed
phase_discovery_instructions  # Replace project= with teamId=, label= with labels=[]
task_discovery_instructions   # Replace project= with teamId=, label= with labels=[]

# Tool Properties (13 methods - return tool names only)
# No changes needed

# Documentation Properties (7 methods × ~2 lines each = 14 lines)
# May need updates for label references
```

**Total Lines to Modify:** ~90 lines

---

**Document Version:** 1.0
**Last Updated:** 2026-02-01
**Status:** Planning Document (Not Implemented)
