from .base import PlatformAdapter


class MarkdownAdapter(PlatformAdapter):
    def __init__(self, base_path: str = '.respec-ai'):
        self.base_path = base_path

    @property
    def phase_discovery_instructions(self) -> str:
        return f"""PHASE_GLOB_PATTERN = "{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME_PARTIAL}}*.md"
PHASE_MATCHES = Glob(pattern=PHASE_GLOB_PATTERN)"""

    @property
    def phase_sync_instructions(self) -> str:
        return f"""TRY:
  PHASE_MARKDOWN = Read({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}.md)
  mcp__respec-ai__store_document(
    doc_type="phase",
    key=f"{{PLAN_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  Display: "✓ Loaded phase '{{PHASE_NAME}}' from Markdown"
EXCEPT:
  Display: "No existing phase file found"
"""

    @property
    def task_sync_instructions(self) -> str:
        return f"""TRY:
  TASK_MARKDOWN = Read({self.base_path}/plans/{{PLAN_NAME}}/phases/tasks/{{TASK_NAME}}.md)
  mcp__respec-ai__store_document(
    doc_type="task",
    key=f"{{PLAN_NAME}}/{{PHASE_NAME}}/{{TASK_NAME}}",
    content=TASK_MARKDOWN
  )
  Display: "✓ Loaded task '{{TASK_NAME}}' from Markdown"
EXCEPT:
  Display: "No existing task file found"
"""

    @property
    def plan_sync_instructions(self) -> str:
        return f"""TRY:
  PLAN_MARKDOWN = Read({self.base_path}/plans/{{PLAN_NAME}}/plan.md)
  mcp__respec-ai__store_document(
    doc_type="plan",
    key=f"{{PLAN_NAME}}",
    content=PLAN_MARKDOWN
  )
  Display: "✓ Loaded plan '{{PLAN_NAME}}' from Markdown"
EXCEPT:
  Display: "No existing plan file found"
"""

    @property
    def config_directory(self) -> str:
        return f'{self.base_path}/config'

    @property
    def phase_location_hint(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/'

    @property
    def plan_discovery_instructions(self) -> str:
        return f"""PLAN_GLOB_PATTERN = "{self.base_path}/plans/*/plan.md"
PLAN_MATCHES = Glob(pattern=PLAN_GLOB_PATTERN)"""

    @property
    def task_discovery_instructions(self) -> str:
        return f"""TASK_GLOB_PATTERN = "{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/{{TASK_NAME_PARTIAL}}*.md"
TASK_MATCHES = Glob(pattern=TASK_GLOB_PATTERN)"""

    @property
    def plan_location_hint(self) -> str:
        return f'{self.base_path}/plans/'

    @property
    def task_location_hint(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/'

    @property
    def create_plan_tool(self) -> str:
        return f'Write({self.base_path}/plans/{{PLAN_NAME}}/plan.md)'

    @property
    def retrieve_plan_tool(self) -> str:
        return f'Read({self.base_path}/plans/{{PLAN_NAME}}/plan.md)'

    @property
    def update_plan_tool(self) -> str:
        return f'Edit({self.base_path}/plans/{{PLAN_NAME}}/plan.md)'

    @property
    def create_plan_completion_tool(self) -> str:
        return f'Write({self.base_path}/plans/{{PLAN_NAME}}/completion-report.md)'

    @property
    def create_phase_tool(self) -> str:
        return f'Write({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}.md)'

    @property
    def retrieve_phase_tool(self) -> str:
        return f'Read({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}.md)'

    @property
    def update_phase_tool(self) -> str:
        return f'Edit({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}.md)'

    @property
    def comment_phase_tool(self) -> str:
        return f'Edit({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}.md)'

    @property
    def create_task_tool(self) -> str:
        return f'Write({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/{{TASK_NAME}}.md)'

    @property
    def retrieve_task_tool(self) -> str:
        return f'Read({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/{{TASK_NAME}}.md)'

    @property
    def update_task_tool(self) -> str:
        return f'Edit({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/{{TASK_NAME}}.md)'

    @property
    def list_phases_tool(self) -> str:
        return f'Glob({self.base_path}/plans/{{PLAN_NAME}}/phases/*.md)'

    @property
    def list_tasks_tool(self) -> str:
        return f'Glob({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/*.md)'

    @property
    def config_location(self) -> str:
        return f'{self.base_path}/config.json'

    @property
    def phase_discovery_pattern(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME_PARTIAL}}*.md'

    @property
    def phase_resource_pattern(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}.md'

    @property
    def task_resource_pattern(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/tasks/{{TASK_NAME}}.md'

    @property
    def plan_resource_example(self) -> str:
        return f'{self.base_path}/plans/PLAN_NAME/plan.md'

    @property
    def phase_resource_example(self) -> str:
        return f'{self.base_path}/plans/X/phases/phase-2a-neo4j-integration.md'

    @property
    def task_location_setup(self) -> str:
        return f'Bash: mkdir -p {self.base_path}/plans/{{{{PLAN_NAME}}}}/phases/{{{{PHASE_NAME}}}}/tasks/'

    @property
    def discovery_tool_invocation(self) -> str:
        return 'Glob(pattern={{PATTERN}})'

    @property
    def platform_tool_documentation(self) -> str:
        return f"""Platform-Specific Tool Usage for Markdown:
- Phase files: Write/Read/Edit for {self.base_path}/plans/{{{{plan_name}}}}/phases/{{{{phase-name}}}}.md
- Discovery: Use Glob patterns to find matching phase files
- Storage: Markdown files in hierarchical directory structure"""
