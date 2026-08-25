from .base import PlatformAdapter


class MarkdownAdapter(PlatformAdapter):
    def __init__(self, base_path: str = '.respec-ai'):
        self.base_path = base_path

    @property
    def phase_discovery_instructions(self) -> str:
        return f"""PHASE_GLOB_PATTERN = "{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME_PARTIAL}}*/phase.md"
PHASE_MATCHES = Glob(pattern=PHASE_GLOB_PATTERN)"""

    @property
    def phase_sync_instructions(self) -> str:
        return f"""TRY:
  PHASE_MARKDOWN = Read({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/phase.md)
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
    def plan_location_hint(self) -> str:
        return f'{self.base_path}/plans/'

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
    def create_phase_tool(self) -> str:
        return f'Write({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/phase.md)'

    @property
    def retrieve_phase_tool(self) -> str:
        return f'Read({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/phase.md)'

    @property
    def update_phase_tool(self) -> str:
        return f'Edit({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/phase.md)'

    @property
    def comment_phase_tool(self) -> str:
        return f'Edit({self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/phase.md)'

    @property
    def phase_location_setup(self) -> str:
        return f'Bash: mkdir -p {self.base_path}/plans/{{{{PLAN_NAME}}}}/phases/{{{{PHASE_NAME}}}}/'

    @property
    def list_phases_tool(self) -> str:
        return f'Glob({self.base_path}/plans/{{PLAN_NAME}}/phases/*/phase.md)'

    @property
    def config_location(self) -> str:
        return f'{self.base_path}/config.json'

    @property
    def phase_discovery_pattern(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME_PARTIAL}}*/phase.md'

    @property
    def phase_resource_pattern(self) -> str:
        return f'{self.base_path}/plans/{{PLAN_NAME}}/phases/{{PHASE_NAME}}/phase.md'

    @property
    def plan_resource_example(self) -> str:
        return f'{self.base_path}/plans/PLAN_NAME/plan.md'

    @property
    def phase_resource_example(self) -> str:
        return f'{self.base_path}/plans/X/phases/phase-2a-neo4j-integration/phase.md'

    @property
    def discovery_tool_invocation(self) -> str:
        return 'Glob(pattern={{PATTERN}})'

    @property
    def platform_tool_documentation(self) -> str:
        return f"""Platform-Specific Tool Usage for Markdown:
- Phase files: Write/Read/Edit for {self.base_path}/plans/{{{{plan_name}}}}/phases/{{{{phase-name}}}}/phase.md
- Discovery: Use Glob patterns to find matching phase files
- Storage: Markdown files in hierarchical directory structure"""
