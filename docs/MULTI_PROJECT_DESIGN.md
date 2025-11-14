# Multi-Project Architecture Design

**Status**: ✅ Phase 1 Complete | ⏸️ Phases 2-4 Planned
**Target Release**: Version 1.1
**Last Updated**: 2025-11-13

## Overview

This document outlines the architecture for supporting multiple projects with a single Specter MCP Server instance. It defines how projects maintain isolation while sharing a common server process.

## Implementation Progress

### What Phase 1 Enables

✅ **Foundation Complete**: All MCP tools now accept explicit `project_path` parameter, establishing the technical foundation for multi-project isolation.

**What Works Now**:
- Tools validate and accept project-specific paths
- Architecture supports multiple projects at the tool level
- Full test coverage ensures reliability

**What Doesn't Work Yet**:
- Commands don't auto-detect project context (manual `project_path` passing required)
- Configuration still stored globally at `~/.specter/projects/`
- State still in-memory (acceptable for MVP, database planned for production)

### Detailed Progress

- ✅ **Phase 1: Tool Signature Updates** (Complete - 2025-11-13)
  - All 36/39 MCP tools updated to accept `project_path` parameter
  - Full test coverage passing (404 tests)
  - Foundation for multi-project isolation established

- ⏸️ **Phase 2: Command Template Updates** (Not Started)
  - Commands need to detect working directory and pass to tools
  - Template generation updates required

- ⏸️ **Phase 3: Local Configuration** (Not Started)
  - Move config from `~/.specter/projects/` to `<project>/.specter/config/`
  - Enable git-trackable, project-local configuration

- 🔄 **Phase 4: State Persistence** (Deferred - Database Approach Planned)
  - Current: InMemoryStateManager works for MVP validation
  - Future: Replace with database-backed state management
  - File-based persistence approach reconsidered in favor of database

## Executive Summary

**Goal**: Enable one Specter MCP Server to serve multiple projects simultaneously with complete isolation of configurations, state, and workflows.

**Approach**: Single global MCP server with explicit project context passing and file-based persistence in per-project directories.

**Key Principles**:
- **Explicit over implicit**: Project context passed explicitly to all tools
- **Local over global**: Configuration and state stored in project directories
- **Isolation by design**: No shared state between projects
- **Git-friendly**: All project data can be version controlled

---

## Architecture Decisions

### Decision 1: Single Global MCP Server

**Choice**: One Specter MCP server instance serves all projects

**Rationale**:
- **Resource efficient**: Single Python process vs N processes for N projects
- **Simpler configuration**: One MCP server entry in `~/.claude/config.json`
- **Easier maintenance**: Updates apply to all projects simultaneously
- **Sufficient isolation**: Project context passed explicitly provides adequate separation

**Trade-offs**:
- Must pass project path explicitly to all tools (more verbose)
- Shared process means shared memory (requires careful state scoping)
- Cannot use `Path.cwd()` for auto-detection

**Alternative Considered**: Per-project MCP server instances
- **Rejected because**: Resource overhead, complex configuration management, unnecessary for isolation needs

### Decision 2: Explicit Project Context

**Choice**: Commands detect working directory and pass `project_path` parameter to all MCP tools

**Implementation**:
```markdown
## Command Template Pattern
1. Detect project context: PROJECT_PATH=$(pwd)
2. Pass to all tools: mcp__specter__create_plan:
                       project_path: $PROJECT_PATH
                       plan_markdown: $CONTENT
```

**Rationale**:
- **Reliability**: No ambiguity about which project is active
- **Debuggability**: Project path visible in all tool calls
- **Compatibility**: Works with single global MCP server architecture
- **No side effects**: No environment variable dependencies

**Trade-offs**:
- Every tool signature requires project_path parameter
- Command templates must include project path detection
- More verbose than auto-detection

**Alternative Considered**: Environment variables
- **Rejected because**: Side-effect-based, harder to debug, fragile across tool boundaries

### Decision 3: Per-Project Local Configuration

**Choice**: Store configuration in `<project>/.specter/config/` instead of `~/.specter/projects/`

**Structure**:
```text
project/
└── .specter/
    └── config/
        └── platform.json
```

**Rationale**:
- **Git-trackable**: Configuration travels with project
- **Self-contained**: Project directories include all needed config
- **No global coupling**: Deleting project directory removes all traces
- **Platform flexibility**: Each project can use different platform (Linear/GitHub/Markdown)

**Trade-offs**:
- Config not centrally accessible
- Each project must be set up individually

**Alternative Considered**: Global configuration at `~/.specter/projects/`
- **Rejected because**: Creates global state, not git-trackable, harder to manage multiple projects

### Decision 4: State Persistence Strategy (Deferred)

**Current Choice**: In-memory state with InMemoryStateManager

**Status**: Acceptable for MVP validation, database planned for production

**Rationale for Deferral**:
- **MVP first**: Prove MCP server architecture works before adding persistence complexity
- **Database preferred**: When persistence is needed, database provides better scalability and transaction support
- **File-based reconsidered**: Originally planned file-based approach replaced by database strategy

**Future Choice**: Database-backed state persistence (SQLite or PostgreSQL)

**Future Benefits**:
- **Survives restarts**: State persists across MCP server restarts
- **Transaction support**: Workflow integrity with ACID guarantees
- **Efficient queries**: Better performance for complex state lookups
- **Industry standard**: Well-understood persistence patterns
- **Scalability**: Handles large projects and concurrent access

**Trade-offs**:
- Adds external dependency (database)
- More complex deployment and configuration
- Requires migration strategy from in-memory

**Alternative Considered**: File-based persistence
- **Reconsidered because**: Database provides better long-term scalability and transaction support

---

## Project Isolation Strategy

### Configuration Isolation

**Loading Pattern**:
```python
def load_project_config(project_path: str) -> ProjectConfig:
    config_file = Path(project_path) / '.specter' / 'config' / 'platform.json'
    if not config_file.exists():
        raise ProjectNotSetupError(f"No Specter config found at {project_path}")
    return ProjectConfig.model_validate_json(config_file.read_text())
```

**Guarantees**:
- ✅ Each project loads its own platform configuration
- ✅ Projects can use different platforms simultaneously
- ✅ Config changes in Project A don't affect Project B
- ✅ No global configuration directory dependencies

### State Isolation

**Current Pattern (In-Memory)**:
```python
class InMemoryStateManager:
    def __init__(self):
        self._plans: dict[str, ProjectPlan] = {}
        self._specs: dict[str, dict[str, TechnicalSpec]] = {}
        self._loops: dict[str, LoopState] = {}

    def store_plan(self, project_id: str, plan: ProjectPlan) -> None:
        self._plans[project_id] = plan

    def get_plan(self, project_id: str) -> ProjectPlan:
        return self._plans[project_id]
```

**Current Guarantees**:
- ✅ State isolated by project_id in memory
- ✅ No cross-project state contamination
- ⚠️ State lost on MCP server restart (acceptable for MVP)

**Future Pattern (Database-Backed)**:
```python
# Planned for post-MVP
class DatabaseStateManager:
    def store_plan(self, project_id: str, plan: ProjectPlan) -> None:
        db.execute(
            "INSERT OR REPLACE INTO plans VALUES (?, ?)",
            (project_id, plan.model_dump_json())
        )
```

**Future Guarantees**:
- ✅ State persists across server restarts
- ✅ Transaction support for workflow integrity
- ✅ Efficient querying and historical tracking

### Workflow Isolation

**Platform-Specific Isolation**:

**Linear Platform**:
- Issues created in user's Linear workspace
- Naturally isolated by Linear workspace boundaries
- Each project's issues tagged with project name
- No cross-project contamination possible

**GitHub Platform**:
- Issues created in specific repository
- Naturally isolated by repository boundaries
- Each project maps to one GitHub repo
- No cross-project contamination possible

**Markdown Platform**:
- Files stored in `.specter/projects/<project-name>/specter-specs/`
- Project name in path ensures isolation
- Each project writes to its own subdirectory
- Risk: Must ensure project names are unique and validated

---

## Code Changes Required

### Phase 1: Tool Signature Updates ✅ COMPLETE

**Status**: Completed 2025-11-13

**Files Updated**: All files in `services/mcp/tools/` (36 tools across 8 modules)

**Implementation Notes**:
- All MCP tools now accept `project_path` as first parameter
- Validation ensures `project_path` is non-empty and properly formatted
- Full test coverage with 404 passing tests
- Foundation established for project isolation

**Example Change**:
```python
# BEFORE
async def create_project_plan(
    project_plan_markdown: str,
    ctx: Context
) -> MCPResponse:
    # Load from global state
    orchestrator = PlatformOrchestrator.create_with_default_config()
    ...

# AFTER
async def create_project_plan(
    project_path: str,  # NEW: Explicit project context
    project_plan_markdown: str,
    ctx: Context
) -> MCPResponse:
    # Load from project-local config
    orchestrator = PlatformOrchestrator.create_for_project(project_path)
    ...
```

**Affected Tool Modules** (All Complete ✅):
- ✅ `project_plan_tools.py` - All plan operations (5 tools)
- ✅ `spec_tools.py` - All spec operations (6 tools)
- ✅ `build_plan_tools.py` - All build plan operations (5 tools)
- ✅ `build_code_tools.py` - All build code operations (3 tools)
- ✅ `loop_tools.py` - All refinement loop operations (5 tools)
- ✅ `feedback_tools_unified.py` - All feedback operations (5 tools)
- ✅ `roadmap_tools.py` - Roadmap operations (2 tools)
- ✅ `plan_completion_report_tools.py` - Completion reports (6 tools)
- ✅ `init_specter_tools.py` - Setup operations (already had project_path)

### Phase 2: Command Template Updates ⏸️ PLANNED

**Status**: Not Started

**Files to Update**: All files in `services/templates/commands/` (~5 commands)

**Pattern to Add**:
```python
# Add to template generation
def generate_plan_command(platform: PlatformType) -> str:
    template = f"""
# Specter Plan Command

## Initialize Context
- Detect project directory: PROJECT_PATH=$(pwd)
- Validate project setup: Check .specter/config/platform.json exists

## Step 1: Create Strategic Plan
Use MCP tool to create plan:

mcp__specter__create_project_plan:
  project_path: $PROJECT_PATH  # Pass explicit context
  project_plan_markdown: $PLAN_CONTENT
"""
    return template
```

**Affected Commands**:
- `plan_command.py`
- `roadmap_command.py`
- `spec_command.py`
- `build_command.py`
- `plan_conversation_command.py`

### Phase 3: Configuration Management Updates ⏸️ PLANNED

**Status**: Not Started

**File**: `services/platform/config_manager.py`

**Changes Required**:
```python
class ConfigManager:
    def __init__(self, project_path: str) -> None:
        # NEW: Use project-local config directory
        self.config_dir = Path(project_path) / '.specter' / 'config'
        self.config_file = self.config_dir / 'platform.json'

    def load_config(self) -> ProjectConfig:
        # Load from project directory, not global
        if not self.config_file.exists():
            raise ProjectNotSetupError(
                f"Project not set up. Run /init-specter in {self.config_dir.parent.parent}"
            )
        return ProjectConfig.model_validate_json(self.config_file.read_text())

    def save_config(self, config: ProjectConfig) -> None:
        # Save to project directory
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(config.model_dump_json(indent=2))
```

**File**: `services/platform/platform_orchestrator.py`

**Changes Required**:
```python
class PlatformOrchestrator:
    # REMOVE this method
    @classmethod
    def create_with_default_config(cls) -> 'PlatformOrchestrator':
        # This creates global config - no longer supported
        pass

    # ADD this method
    @classmethod
    def create_for_project(cls, project_path: str) -> 'PlatformOrchestrator':
        """Create orchestrator for specific project.

        Args:
            project_path: Absolute path to project directory

        Returns:
            PlatformOrchestrator configured for the project

        Raises:
            ProjectNotSetupError: If project not set up with /init-specter
        """
        config_manager = ConfigManager(project_path)
        config = config_manager.load_config()
        return cls(config, project_path)
```

### Phase 4: State Persistence Updates 🔄 DEFERRED

**Status**: Deferred - Database approach planned instead

**Strategic Decision**: After MCP server validation, state persistence will be implemented with a database backend rather than file-based storage. This provides:
- Better scalability for multi-project scenarios
- Transaction support for workflow integrity
- Efficient querying and state management
- Industry-standard persistence patterns

**Current Approach Works**: InMemoryStateManager is sufficient for MVP validation and development.

**Original File-Based Approach** (Replaced by database plan):
```python
from pathlib import Path
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class FileStateManager(Generic[T]):
    """Manages file-based state persistence for project workflows."""

    def __init__(self, project_path: str, state_type: str):
        """Initialize state manager.

        Args:
            project_path: Absolute path to project directory
            state_type: State category (plans, specs, loops)
        """
        self.state_dir = Path(project_path) / '.specter' / 'state' / state_type
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, data: T) -> None:
        """Save state to file."""
        state_file = self.state_dir / f'{name}.json'
        state_file.write_text(data.model_dump_json(indent=2))

    def load(self, name: str, model: type[T]) -> T | None:
        """Load state from file."""
        state_file = self.state_dir / f'{name}.json'
        if not state_file.exists():
            return None
        return model.model_validate_json(state_file.read_text())

    def list(self) -> list[str]:
        """List all state files."""
        return [f.stem for f in self.state_dir.glob('*.json')]

    def delete(self, name: str) -> bool:
        """Delete state file."""
        state_file = self.state_dir / f'{name}.json'
        if state_file.exists():
            state_file.unlink()
            return True
        return False
```

**Update Existing Tools**:
```python
# In project_plan_tools.py
class ProjectPlanTools:
    def __init__(self, state: StateManager) -> None:
        self.state = state
        # REMOVE: self._project_plans: dict[str, ProjectPlan] = {}
        # State now persisted to files, not in-memory

    def store_project_plan(
        self,
        project_path: str,  # NEW parameter
        project_plan: ProjectPlan
    ) -> MCPResponse:
        # Save to project-local state
        state_manager = FileStateManager[ProjectPlan](project_path, 'plans')
        state_manager.save(project_plan.project_name, project_plan)
        return MCPResponse(success=True, message="Plan stored successfully")

    def get_project_plan_data(
        self,
        project_path: str,  # NEW parameter
        project_name: str
    ) -> ProjectPlan | None:
        # Load from project-local state
        state_manager = FileStateManager[ProjectPlan](project_path, 'plans')
        return state_manager.load(project_name, ProjectPlan)
```

---

## Installation & Setup Flow

### One-Time: MCP Server Installation

**User performs once, globally**:

```bash
# 1. Clone Specter repository
cd ~/coding/projects
git clone git@github.com:mmcclatchy/specter.git
cd specter

# 2. Install dependencies
uv sync

# 3. Configure MCP server in Claude Code
# Edit ~/.claude/config.json:
{
  "mcpServers": {
    "specter": {
      "command": "uv",
      "args": ["run", "specter-server"],
      "cwd": "/absolute/path/to/specter"
    }
  }
}

# 4. Verify
claude
/mcp list  # Should show "specter" with 32 tools
```

### Per-Project: Project Setup

**User performs for each project**:

```bash
# 1. Navigate to project
cd /path/to/my-project

# 2. Run installer (optional - just creates setup command)
~/coding/projects/specter/scripts/install-specter.sh

# 3. Setup project with Claude Code
claude

# In Claude Code:
/init-specter markdown  # or linear, github

# This creates:
# - .claude/commands/specter-*.md
# - .claude/agents/*.md
# - .specter/config/platform.json
# - .specter/state/ (created on first workflow)
```

### Workflow Usage

**User works on any project**:

```bash
# Switch to Project A
cd /path/to/project-a
claude

# Commands automatically use Project A's config
/specter-plan my-feature
# Creates plan in .specter/state/plans/my-feature.json

# Switch to Project B
cd /path/to/project-b
claude

# Commands automatically use Project B's config
/specter-plan another-feature
# Creates plan in .specter/state/plans/another-feature.json
# No interference with Project A
```

---

## Testing Strategy

### Unit Tests

**Test File**: `tests/unit/test_multi_project_isolation.py`

**Test Cases**:
```python
def test_config_loads_from_project_directory():
    """Config manager loads from project-local .specter/config/"""

def test_state_saves_to_project_directory():
    """State manager saves to project-local .specter/state/"""

def test_projects_use_different_platforms():
    """Project A can use Linear while Project B uses Markdown"""

def test_project_path_required_in_tools():
    """All MCP tools require project_path parameter"""
```

### Integration Tests

**Test File**: `tests/integration/test_multi_project_workflows.py`

**Test Scenarios**:
```python
@pytest.fixture
def setup_two_projects(tmp_path):
    """Create two test projects with different platforms"""
    project_a = tmp_path / 'project-a'
    project_b = tmp_path / 'project-b'
    # Setup both projects
    return project_a, project_b

def test_concurrent_plan_creation(setup_two_projects):
    """Create plans in both projects simultaneously"""
    project_a, project_b = setup_two_projects

    # Create plan in project A
    plan_a = create_project_plan(str(project_a), "Plan A content")

    # Create plan in project B
    plan_b = create_project_plan(str(project_b), "Plan B content")

    # Verify isolation
    assert get_project_plan(str(project_a), "Plan A") is not None
    assert get_project_plan(str(project_b), "Plan B") is not None
    assert get_project_plan(str(project_a), "Plan B") is None  # Not cross-contaminated

def test_different_platforms_simultaneously(setup_two_projects):
    """Project A uses Linear, Project B uses Markdown"""

def test_state_persists_across_restarts(setup_two_projects):
    """State files persist when MCP server restarts"""
```

### End-to-End Tests

**Test File**: `tests/e2e/test_multi_project_production.py`

**Test Workflows**:
```python
def test_full_workflow_project_a():
    """Complete workflow: plan → roadmap → spec → build in Project A"""

def test_full_workflow_project_b():
    """Complete workflow in Project B with different platform"""

def test_switch_between_projects():
    """Start workflow in A, switch to B, return to A"""
```

---

## Migration Path

### For Existing Single-Project Users

**Current Setup** (before multi-project):
- Config at `~/.specter/projects/<sanitized-path>/platform.json`
- In-memory state only
- Works with single project

**Migration Steps**:

1. **Backup existing config** (optional):
   ```bash
   cp -r ~/.specter ~/specter-backup
   ```

2. **Run /init-specter again**:
   ```bash
   cd /path/to/existing-project
   claude
   /init-specter <your-platform>
   ```
   This creates `.specter/config/platform.json` in project directory

3. **State will be empty** (expected):
   - Old in-memory state is lost (was temporary anyway)
   - New workflows will use file-based persistence
   - Previous plans/specs on Linear/GitHub/Markdown still accessible via platform

4. **Delete old global config** (optional cleanup):
   ```bash
   rm -rf ~/.specter
   ```

### For New Users

No migration needed - follow standard installation flow in USER_GUIDE.md

---

## Known Limitations & Future Improvements

### Current Limitations

1. **In-memory state only**: State lost on MCP server restart (acceptable for MVP)
2. **Global configuration**: Config still at `~/.specter/projects/` instead of project-local
3. **Manual project context**: Commands require explicit `project_path` parameter
4. **No cross-project workflows**: Can't reference specs from Project A in Project B

### Future Enhancements

**Version 1.2: Database-Backed State** (Deferred)
- Replace InMemoryStateManager with database backend (SQLite or PostgreSQL)
- Persistent state across server restarts
- Transaction support for workflow integrity
- Efficient querying and state management
- State archival for historical tracking

**Version 1.3: Cross-Project Features**
- Reference specs from other projects
- Shared template libraries across projects
- Multi-project roadmaps

**Version 1.4: Advanced Isolation**
- Project name validation and uniqueness checks
- Config version tracking and auto-migration
- State backup and restore utilities

---

## Security Considerations

### Path Validation

**Risk**: Malicious project_path could access files outside project

**Mitigation**:
```python
def validate_project_path(project_path: str) -> None:
    """Validate project path is safe."""
    path = Path(project_path).resolve()

    # Must be absolute
    if not path.is_absolute():
        raise ValueError("Project path must be absolute")

    # Must exist
    if not path.exists():
        raise ValueError("Project path must exist")

    # Must be a directory
    if not path.is_dir():
        raise ValueError("Project path must be a directory")

    # Must not be system directories
    system_dirs = ['/etc', '/sys', '/proc', '/dev', '/var']
    if any(str(path).startswith(d) for d in system_dirs):
        raise ValueError("Cannot use system directories as project path")
```

### File System Isolation

**Risk**: Path traversal in project names

**Mitigation**:
```python
def sanitize_project_name(name: str) -> str:
    """Sanitize project name for file system safety."""
    # Remove path separators
    safe_name = name.replace('/', '_').replace('\\', '_')
    # Remove dangerous characters
    safe_name = re.sub(r'[^\w\-_]', '_', safe_name)
    # Limit length
    return safe_name[:100]
```

### Configuration Validation

**Risk**: Malicious platform.json could execute code

**Mitigation**:
- Use Pydantic models for strict validation
- No eval() or exec() on config contents
- Only allow known platform types: linear, github, markdown

---

## Performance Considerations

### Current In-Memory State

**Impact**: Fast access, no I/O overhead

**Advantages**:
- Instant state access (no disk I/O)
- Simple implementation for MVP
- Predictable performance characteristics

**Limitations**:
- State lost on server restart
- Memory growth with many projects/workflows
- No persistence for long-running workflows

### Future Database State

**Planned Optimizations**:
1. **Connection pooling**: Reuse database connections across requests
2. **Query optimization**: Indexed lookups for fast state retrieval
3. **Batch operations**: Group multiple state updates into transactions
4. **Caching layer**: In-memory cache for frequently accessed state

### Memory Management

**Impact**: Single server process shared across projects

**Monitoring**:
- Track memory usage per project context
- Log memory pressure warnings
- Implement state eviction if needed (in-memory)
- Database handles persistence once implemented

**Best Practices**:
- Don't load all project state at startup
- Clean up state objects after command completion
- Use generators for large list operations
- Database will provide natural state offloading

---

## Appendix: Architecture Diagrams

### Single MCP Server with Multiple Projects

```text
┌─────────────────────────────────────────┐
│      Claude Code (User Interface)       │
│                                         │
│  Working Dir: /path/to/project-a        │
│  Commands: /specter-plan, /specter-spec │
└────────────────┬────────────────────────┘
                 │
                 │ MCP Protocol
                 │
┌────────────────▼────────────────────────┐
│      Specter MCP Server (Single)        │
│      Location: ~/coding/projects/       │
│                specter/                 │
│                                         │
│  Receives: project_path parameter       │
│  Routes to: Project-specific handler    │
└────────────────┬────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
┌────────▼─────┐  ┌─────▼────────┐
│  Project A   │  │  Project B   │
│              │  │              │
│  .specter/   │  │  .specter/   │
│  ├─config/   │  │  ├─config/   │
│  └─state/    │  │  └─state/    │
└──────────────┘  └──────────────┘
```

### State Isolation Flow (Current In-Memory)

```text
User in Project A           Specter MCP Server              Memory State
─────────────────           ──────────────────              ────────────

/specter-plan ──────────────> create_project_plan()
                              project_path="/path/a"
                              │
                              ├─ Load config from
                              │  ~/.specter/projects/     ◄─── platform.json
                              │
                              ├─ Create plan
                              │
                              └─ Store in memory:
                                 state_manager._plans[
                                   "project-a"
                                 ] = plan                  ───► In-Memory Dict


User in Project B           Specter MCP Server              Memory State
─────────────────           ──────────────────              ────────────

/specter-plan ──────────────> create_project_plan()
                              project_path="/path/b"
                              │
                              ├─ Load config from
                              │  ~/.specter/projects/     ◄─── platform.json
                              │
                              ├─ Create plan (isolated)
                              │
                              └─ Store in memory:
                                 state_manager._plans[
                                   "project-b"
                                 ] = plan                  ───► In-Memory Dict
                                                                (separate key)
```

**Note**: Future database implementation will replace in-memory storage with persistent database records.

---

## Summary

This multi-project architecture provides:

✅ **Single global MCP server** - Efficient resource usage
✅ **Explicit project context** - Clear, debuggable tool calls (Phase 1 Complete)
⏸️ **Local configuration** - Git-trackable, self-contained projects (Planned)
🔄 **Database persistence** - State survives restarts (Deferred until post-MVP)
⏸️ **Complete isolation** - No cross-project interference (Partial - tool level only)
⏸️ **Platform flexibility** - Each project can use different platform (Planned)

**Implementation Status**:
- ✅ Phase 1 Complete (Tool signatures) - 2025-11-13
- ⏸️ Phase 2 Planned (Command templates)
- ⏸️ Phase 3 Planned (Local configuration)
- 🔄 Phase 4 Deferred (Database instead of file-based state)

**Next Steps**:
1. Phase 2: Update command templates to pass `project_path` from `$(pwd)`
2. Phase 3: Move configuration from global to project-local directories
3. Validate MCP server with current in-memory state
4. Phase 4 (Future): Replace InMemoryStateManager with database backend

**Current USER_GUIDE.md Status**: Should be updated to reflect Phase 1 completion

---

**Document Version**: 1.1
**Author**: Specter Development Team
**Review Status**: Phase 1 Complete - Phases 2-4 Ready for Implementation
**Last Reviewed**: 2025-11-13
