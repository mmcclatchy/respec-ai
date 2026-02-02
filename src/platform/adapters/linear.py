from .base import PlatformAdapter


class LinearAdapter(PlatformAdapter):
    @property
    def phase_discovery_instructions(self) -> str:
        return """PHASE_LIST_RESULT = mcp__linear-server__list_issues(
  project={PLAN_NAME},
  title_contains={PHASE_NAME_PARTIAL},
  label='phase'
)
PHASE_MATCHES = [issue.title for issue in PHASE_LIST_RESULT.issues]"""

    @property
    def phase_sync_instructions(self) -> str:
        return """TRY:
  PHASE_RESULT = mcp__linear-server__get_issue(
    project={PLAN_NAME},
    title={PHASE_NAME},
    label='phase'
  )
  mcp__respec-ai__store_document(
    doc_type="phase",
    key=f"{PLAN_NAME}/{PHASE_NAME}",
    content=PHASE_RESULT.description
  )
  Display: "✓ Loaded phase '{PHASE_NAME}' from Linear"
EXCEPT:
  Display: "No existing phase found in Linear"
"""

    @property
    def task_sync_instructions(self) -> str:
        return """TRY:
  TASK_RESULT = mcp__linear-server__get_issue(
    project={PLAN_NAME},
    title={TASK_NAME},
    label='task'
  )
  mcp__respec-ai__store_document(
    doc_type="task",
    key=f"{PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}",
    content=TASK_RESULT.description
  )
  Display: "✓ Loaded task '{TASK_NAME}' from Linear"
EXCEPT:
  Display: "No existing task found in Linear"
"""

    @property
    def plan_sync_instructions(self) -> str:
        return """TRY:
  PLAN_RESULT = mcp__linear-server__get_document(project={PLAN_NAME})
  mcp__respec-ai__store_document(
    doc_type="plan",
    key=f"{PLAN_NAME}",
    content=PLAN_RESULT.content
  )
  Display: "✓ Loaded plan '{PLAN_NAME}' from Linear"
EXCEPT:
  Display: "No existing plan document found in Linear"
"""

    @property
    def coding_standards_location(self) -> str:
        return 'Linear project custom field: coding_standards'

    @property
    def phase_location_hint(self) -> str:
        return 'Linear project: {PLAN_NAME}'

    @property
    def plan_discovery_instructions(self) -> str:
        return """PLAN_LIST_RESULT = mcp__linear-server__list_projects()
PLAN_MATCHES = [project.name for project in PLAN_LIST_RESULT.projects]"""

    @property
    def task_discovery_instructions(self) -> str:
        return """TASK_LIST_RESULT = mcp__linear-server__list_issues(
  project={PLAN_NAME},
  title_contains={TASK_NAME_PARTIAL},
  label='task'
)
TASK_MATCHES = [issue.title for issue in TASK_LIST_RESULT.issues]"""

    @property
    def plan_location_hint(self) -> str:
        return 'Linear workspace projects'

    @property
    def task_location_hint(self) -> str:
        return 'Linear project: {PLAN_NAME}, phase: {PHASE_NAME}'

    @property
    def coding_standards_read_instruction(self) -> str:
        return """Read coding standards from Phase custom field or Phase Code Standards section.

**If custom field 'coding_standards' exists**:
- Apply ALL rules from custom field to generated code

**If custom field does not exist**:
- Use Phase Code Standards section as fallback
- Apply general Python best practices (PEP 8)
- Minimal comments, self-documenting code
- Full type hints on all functions"""

    @property
    def create_plan_tool(self) -> str:
        return 'mcp__linear-server__create_project'

    @property
    def retrieve_plan_tool(self) -> str:
        return 'mcp__linear-server__get_document'

    @property
    def update_plan_tool(self) -> str:
        return 'mcp__linear-server__update_document'

    @property
    def create_plan_completion_tool(self) -> str:
        return 'mcp__linear-server__create_issue'

    @property
    def create_phase_tool(self) -> str:
        return 'mcp__linear-server__create_issue'

    @property
    def retrieve_phase_tool(self) -> str:
        return 'mcp__linear-server__get_issue'

    @property
    def update_phase_tool(self) -> str:
        return 'mcp__linear-server__update_issue'

    @property
    def comment_phase_tool(self) -> str:
        return 'mcp__linear-server__create_comment'

    @property
    def create_task_tool(self) -> str:
        return 'mcp__linear-server__create_issue'

    @property
    def retrieve_task_tool(self) -> str:
        return 'mcp__linear-server__get_issue'

    @property
    def update_task_tool(self) -> str:
        return 'mcp__linear-server__update_issue'

    @property
    def list_phases_tool(self) -> str:
        return 'mcp__linear-server__list_issues'

    @property
    def list_tasks_tool(self) -> str:
        return 'mcp__linear-server__list_issues'

    @property
    def config_location(self) -> str:
        return 'Linear project custom field: config'

    @property
    def phase_discovery_pattern(self) -> str:
        return 'N/A - Linear uses MCP query instead of pattern matching'

    @property
    def phase_resource_pattern(self) -> str:
        return 'Linear issue: {PLAN_NAME}/{PHASE_NAME} (label: phase)'

    @property
    def task_resource_pattern(self) -> str:
        return 'Linear issue: {PLAN_NAME}/{TASK_NAME} (label: task)'

    @property
    def plan_resource_example(self) -> str:
        return 'Linear project: PLAN_NAME'

    @property
    def phase_resource_example(self) -> str:
        return 'Linear issue: project-x/phase-2a-neo4j-integration (label: phase)'

    @property
    def task_location_setup(self) -> str:
        return 'N/A - Linear manages structure via platform'

    @property
    def discovery_tool_invocation(self) -> str:
        return 'mcp__linear-server__list_issues(...)'

    @property
    def platform_tool_documentation(self) -> str:
        return """Platform-Specific Tool Usage for Linear:
- Phase resources: mcp__linear-server__create_issue, get_issue, update_issue (with label='phase')
- Discovery: Use Linear MCP server list_issues with filters
- Storage: Linear issues and projects managed via Linear platform"""
