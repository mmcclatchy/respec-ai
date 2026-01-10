from .base import PlatformAdapter


class GitHubAdapter(PlatformAdapter):
    @property
    def phase_discovery_instructions(self) -> str:
        return """PHASE_LIST_RESULT = mcp__github__list_milestones(
  repo={PLAN_NAME},
  state='all'
)
PHASE_MATCHES = [ms.title for ms in PHASE_LIST_RESULT if '{PHASE_NAME_PARTIAL}' in ms.title]"""

    @property
    def phase_sync_instructions(self) -> str:
        return """TRY:
  PHASE_RESULT = mcp__github__get_milestone(
    repo={PLAN_NAME},
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

    @property
    def task_sync_instructions(self) -> str:
        return """TRY:
  TASK_RESULT = mcp__github__get_issue(
    repo={PLAN_NAME},
    title={TASK_NAME}
  )
  mcp__respec-ai__store_document(
    doc_type="task",
    key=f"{PLAN_NAME}/{PHASE_NAME}/{TASK_NAME}",
    content=TASK_RESULT.body
  )
  Display: "✓ Loaded task '{TASK_NAME}' from GitHub"
EXCEPT:
  Display: "No existing task found in GitHub"
"""

    @property
    def plan_sync_instructions(self) -> str:
        return """TRY:
  PLAN_RESULT = mcp__github__get_file(
    repo={PLAN_NAME},
    path=".respec-ai/plan.md"
  )
  mcp__respec-ai__store_document(
    doc_type="plan",
    key=f"{PLAN_NAME}",
    content=PLAN_RESULT.content
  )
  Display: "✓ Loaded plan '{PLAN_NAME}' from GitHub"
EXCEPT:
  Display: "No existing plan file found in GitHub"
"""

    @property
    def coding_standards_location(self) -> str:
        return '.respec-ai/coding-standards.md (in repository)'

    @property
    def phase_location_hint(self) -> str:
        return 'GitHub repo: {PLAN_NAME}'

    @property
    def store_phase_tool_reference(self) -> str:
        return 'mcp__respec-ai__store_document(doc_type="phase", key=f"{PLAN_NAME}/{PHASE_NAME}", content=PHASE_RESULT.description)'

    @property
    def retrieve_phase_tool_reference(self) -> str:
        return 'mcp__respec-ai__get_document(doc_type="phase", key=f"{PLAN_NAME}/{PHASE_NAME}")'

    @property
    def retrieve_task_tool_reference(self) -> str:
        return 'mcp__respec-ai__get_document(doc_type="task", loop_id="{task_loop_id}")'

    @property
    def plan_discovery_instructions(self) -> str:
        return """PLAN_LIST_RESULT = mcp__github__list_repositories()
PLAN_MATCHES = [repo.name for repo in PLAN_LIST_RESULT.repositories]"""

    @property
    def task_discovery_instructions(self) -> str:
        return """TASK_LIST_RESULT = mcp__github__list_issues(
  repo={PLAN_NAME},
  label='task',
  milestone={PHASE_NAME},
  title_contains={task_name_partial}
)
TASK_MATCHES = [issue.title for issue in TASK_LIST_RESULT.issues]"""

    @property
    def plan_location_hint(self) -> str:
        return 'GitHub repositories'

    @property
    def task_location_hint(self) -> str:
        return 'GitHub repo: {PLAN_NAME}, milestone: {PHASE_NAME}'

    @property
    def coding_standards_read_instruction(self) -> str:
        return """Read coding standards from .respec-ai/coding-standards.md in repository.

**If file exists in repo**:
- Apply ALL rules from coding-standards.md to generated code

**If file does not exist**:
- Use Phase Code Standards section as fallback
- Apply general Python best practices (PEP 8)
- Minimal comments, self-documenting code
- Full type hints on all functions"""

    @property
    def create_plan_tool(self) -> str:
        return 'mcp__github__create_repository(name={PLAN_NAME})'

    @property
    def retrieve_plan_tool(self) -> str:
        return "mcp__github__get_file(repo={PLAN_NAME}, path='.respec-ai/plan.md')"

    @property
    def update_plan_tool(self) -> str:
        return "mcp__github__update_file(repo={PLAN_NAME}, path='.respec-ai/plan.md')"

    @property
    def create_plan_completion_tool(self) -> str:
        return "mcp__github__create_issue(repo={PLAN_NAME}, title='Completion Report', labels=['completion'])"

    @property
    def create_phase_tool(self) -> str:
        return 'mcp__github__create_milestone(repo={PLAN_NAME}, title={PHASE_NAME})'

    @property
    def retrieve_phase_tool(self) -> str:
        return 'mcp__github__get_milestone(repo={PLAN_NAME}, title={PHASE_NAME})'

    @property
    def update_phase_tool(self) -> str:
        return 'mcp__github__update_milestone(repo={PLAN_NAME}, title={PHASE_NAME})'

    @property
    def comment_phase_tool(self) -> str:
        return 'mcp__github__create_milestone_comment(repo={PLAN_NAME}, milestone={PHASE_NAME})'

    @property
    def create_task_tool(self) -> str:
        return "mcp__github__create_issue(repo={PLAN_NAME}, title={TASK_NAME}, milestone={PHASE_NAME}, labels=['task'])"

    @property
    def retrieve_task_tool(self) -> str:
        return 'mcp__github__get_issue(repo={PLAN_NAME}, title={TASK_NAME})'

    @property
    def update_task_tool(self) -> str:
        return 'mcp__github__update_issue(repo={PLAN_NAME}, title={TASK_NAME})'

    @property
    def list_phases_tool(self) -> str:
        return 'mcp__github__list_milestones(repo={PLAN_NAME})'

    @property
    def list_tasks_tool(self) -> str:
        return "mcp__github__list_issues(repo={PLAN_NAME}, milestone={PHASE_NAME}, labels=['task'])"

    @property
    def config_location(self) -> str:
        return '.respec-ai/config.json (in repository)'

    @property
    def phase_discovery_pattern(self) -> str:
        return 'N/A - GitHub uses milestone query'

    @property
    def phase_resource_pattern(self) -> str:
        return 'GitHub milestone: {PLAN_NAME}/{PHASE_NAME}'

    @property
    def task_resource_pattern(self) -> str:
        return 'GitHub issue: {PLAN_NAME}/{TASK_NAME} (milestone: {PHASE_NAME})'

    @property
    def plan_resource_example(self) -> str:
        return 'GitHub repository: PLAN_NAME/.respec-ai/plan.md'

    @property
    def phase_resource_example(self) -> str:
        return 'GitHub milestone: project-x/phase-2a-neo4j-integration'

    @property
    def task_location_setup(self) -> str:
        return 'N/A - GitHub manages structure via platform'

    @property
    def discovery_tool_invocation(self) -> str:
        return 'mcp__github__list_milestones(...)'

    @property
    def platform_tool_documentation(self) -> str:
        return """Platform-Specific Tool Usage for GitHub:
- Phase resources: mcp__github__create_milestone, get_milestone, update_milestone
- Discovery: Use GitHub MCP server list_milestones and list_issues
- Storage: GitHub milestones and issues managed via GitHub platform"""
