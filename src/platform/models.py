"""Pydantic models for platform configuration with fail-fast validation."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from .platform_selector import PlatformType
from .tool_enums import (
    AbstractOperation,
    BuiltInTool,
    CommandTemplate,
    ExternalPlatformTool,
    ToolEnums,
)


class PlatformModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        extra='forbid',  # Fail if unexpected fields provided
    )


class PlatformRequest(PlatformModel):
    project_path: Path = Field(description='Absolute path to the project')

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: Path) -> Path:
        if not v.is_absolute():
            raise ValueError('Project path must be absolute')
        return v


class PlatformRequirements(PlatformModel):
    supports_issues: bool = Field(description='Platform must support issue tracking')
    supports_comments: bool = Field(description='Platform must support commenting on items')
    supports_projects: bool = Field(default=False, description='Platform must support project management')
    supports_labels: bool = Field(default=False, description='Platform must support labeling/tagging')
    real_time_collaboration: bool = Field(default=False, description='Platform must support real-time collaboration')
    external_integration: bool = Field(default=False, description='Platform must support external integrations')


class ProjectSetupRequest(PlatformRequest):
    platform: PlatformType = Field(description='Platform to use for this project')
    requirements: PlatformRequirements = Field(description='Platform requirements that must be met')


class ProjectSetupWithRecommendationRequest(PlatformRequest):
    requirements: PlatformRequirements = Field(description='Platform requirements for recommendation')


class ProjectPlatformChangeRequest(PlatformRequest):
    new_platform: PlatformType = Field(description='New platform to use')
    requirements: PlatformRequirements | None = Field(
        default=None, description='Optional new requirements - if not provided, existing requirements are kept'
    )


class TemplateGenerationRequest(PlatformRequest):
    command_name: CommandTemplate = Field(description='Name of the command template to generate')


class ProjectConfig(PlatformRequest):
    platform: PlatformType = Field(description='Platform configured for this project')
    requirements: PlatformRequirements = Field(description='Platform requirements for this project')
    config_data: dict[str, Any] = Field(default_factory=dict, description='Additional configuration data')


class ToolReference(PlatformModel):
    tool: ToolEnums = Field(description='The specific tool to reference')
    parameters: str = Field(default='', description='Tool parameters like path patterns or agent names')

    def render(self) -> str:
        if self.parameters:
            return f'{self.tool.value}({self.parameters})'
        return self.tool.value

    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: str, info: Any) -> str:
        if not v:
            return v

        tool = info.data.get('tool')
        if not tool:
            return v

        # Validate path patterns for file operations
        if tool in [BuiltInTool.READ, BuiltInTool.WRITE, BuiltInTool.EDIT, BuiltInTool.GLOB]:
            if not v.strip():
                raise ValueError(f'File operation tool {tool.value} requires non-empty path parameter')
            # Basic path pattern validation
            if '..' in v:
                raise ValueError(f'Path parameter cannot contain directory traversal: {v}')

        # Validate agent names for Task tool
        elif tool == BuiltInTool.TASK:
            if not v.strip():
                raise ValueError('Task tool requires non-empty agent name parameter')
            # Skip validation for special platform tool markers
            if v.startswith('__PLATFORM_TOOL__'):
                return v
            # Basic agent name validation
            if not v.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f'Agent name can only contain letters, numbers, hyphens, and underscores: {v}')

        return v


class PlatformToolMapping(PlatformModel):
    operation: AbstractOperation = Field(description='The abstract operation being mapped')
    linear_tool: ToolReference | None = Field(default=None, description='Tool for Linear platform')
    github_tool: ToolReference | None = Field(default=None, description='Tool for GitHub platform')
    markdown_tool: ToolReference | None = Field(default=None, description='Tool for Markdown platform')

    @field_validator('linear_tool')
    @classmethod
    def validate_linear_tool(cls, v: ToolReference | None) -> ToolReference | None:
        if v and isinstance(v.tool, ExternalPlatformTool):
            if not v.tool.value.startswith('mcp__linear-server__'):
                raise ValueError(f'Linear platform tool must be a Linear server tool, got: {v.tool.value}')
        return v

    @field_validator('github_tool')
    @classmethod
    def validate_github_tool(cls, v: ToolReference | None) -> ToolReference | None:
        if v and isinstance(v.tool, ExternalPlatformTool):
            if not v.tool.value.startswith('mcp__github__'):
                raise ValueError(f'GitHub platform tool must be a GitHub tool, got: {v.tool.value}')
        return v

    @field_validator('markdown_tool')
    @classmethod
    def validate_markdown_tool(cls, v: ToolReference | None) -> ToolReference | None:
        if v and not isinstance(v.tool, BuiltInTool):
            raise ValueError(f'Markdown platform must use built-in tools, got: {v.tool.value}')
        return v

    def get_tool_for_platform(self, platform: PlatformType) -> ToolReference | None:
        if platform == PlatformType.LINEAR:
            return self.linear_tool
        elif platform == PlatformType.GITHUB:
            return self.github_tool
        elif platform == PlatformType.MARKDOWN:
            return self.markdown_tool
        else:
            raise ValueError(f'Unknown platform: {platform}')

    def render_tool_for_platform(self, platform: PlatformType) -> str | None:
        tool_ref = self.get_tool_for_platform(platform)
        return tool_ref.render() if tool_ref else None


class SpecCommandTools(BaseModel):
    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_spec_tool: str = Field(..., description='Platform-specific tool for creating specs')
    get_spec_tool: str = Field(..., description='Platform-specific tool for retrieving specs')
    update_spec_tool: str = Field(..., description='Platform-specific tool for updating specs')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    @computed_field
    def create_spec_tool_interpolated(self) -> str:
        if '*' not in self.create_spec_tool:
            return self.create_spec_tool
        return self.create_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def get_spec_tool_interpolated(self) -> str:
        if '*' not in self.get_spec_tool:
            return self.get_spec_tool
        return self.get_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def update_spec_tool_interpolated(self) -> str:
        if '*' not in self.update_spec_tool:
            return self.update_spec_tool
        return self.update_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def sync_project_plan_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return """PLAN_MARKDOWN = Read(.respec-ai/projects/{PLAN_NAME}/project_plan.md)
mcp__respec-ai__store_project_plan(project_name=PLAN_NAME, project_plan_markdown=PLAN_MARKDOWN)"""
        elif self.platform == PlatformType.LINEAR:
            return """PLAN_RESULT = mcp__linear-server__get_document(project_name=PLAN_NAME)
mcp__respec-ai__store_project_plan(project_name=PLAN_NAME, project_plan_markdown=PLAN_RESULT.content)"""
        elif self.platform == PlatformType.GITHUB:
            return """PLAN_RESULT = mcp__github__get_file(path=".respec-ai/projects/{PLAN_NAME}/project_plan.md")
mcp__respec-ai__store_project_plan(project_name=PLAN_NAME, project_plan_markdown=PLAN_RESULT.content)"""
        else:
            return """# Platform sync not configured"""

    @computed_field
    def sync_spec_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return """SPEC_MARKDOWN = Read(.respec-ai/projects/{PROJECT_NAME}/respec-specs/{SPEC_NAME}.md)
mcp__respec-ai__store_spec(project_name=PROJECT_NAME, spec_name=SPEC_NAME, spec_markdown=SPEC_MARKDOWN)"""
        elif self.platform == PlatformType.LINEAR:
            return """SPEC_RESULT = mcp__linear-server__get_issue(spec_name=SPEC_NAME)
mcp__respec-ai__store_spec(project_name=PROJECT_NAME, spec_name=SPEC_NAME, spec_markdown=SPEC_RESULT.description)"""
        elif self.platform == PlatformType.GITHUB:
            return """SPEC_RESULT = mcp__github__get_issue(issue_title=SPEC_NAME)
mcp__respec-ai__store_spec(project_name=PROJECT_NAME, spec_name=SPEC_NAME, spec_markdown=SPEC_RESULT.body)"""
        else:
            return """# Platform sync not configured"""


class PlanCommandTools(BaseModel):
    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_project_external: str = Field(..., description='Platform-specific tool for creating external project')
    create_project_completion_external: str = Field(
        ..., description='Platform-specific tool for creating external project completion'
    )
    get_project_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    @computed_field
    def create_project_tool_interpolated(self) -> str:
        if '*' not in self.create_project_external:
            return self.create_project_external
        return self.create_project_external.replace('*', '{project_name}')

    @computed_field
    def create_completion_tool_interpolated(self) -> str:
        if '*' not in self.create_project_completion_external:
            return self.create_project_completion_external
        return self.create_project_completion_external.replace('*', '{project_name}')

    @computed_field
    def get_project_plan_tool_interpolated(self) -> str:
        if '*' not in self.get_project_plan_tool:
            return self.get_project_plan_tool
        return self.get_project_plan_tool.replace('*', '{project_name}')

    @computed_field
    def sync_project_plan_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return """TRY:
  PLAN_MARKDOWN = Read(.respec-ai/projects/{PROJECT_NAME}/project_plan.md)
  mcp__respec-ai__store_project_plan(
    project_name=PROJECT_NAME,
    project_plan_markdown=PLAN_MARKDOWN
  )
  Display: "✓ Loaded existing project plan from platform"
EXCEPT:
  Display: "No existing project plan found - will create new"
"""
        elif self.platform == PlatformType.LINEAR:
            return """TRY:
  PLAN_RESULT = mcp__linear-server__get_document(project_name=PROJECT_NAME)
  PLAN_MARKDOWN = PLAN_RESULT.content
  mcp__respec-ai__store_project_plan(
    project_name=PROJECT_NAME,
    project_plan_markdown=PLAN_MARKDOWN
  )
  Display: "✓ Loaded existing project plan from platform"
EXCEPT:
  Display: "No existing project plan found - will create new"
"""
        elif self.platform == PlatformType.GITHUB:
            return """TRY:
  PLAN_RESULT = mcp__github__get_file(path=".respec-ai/projects/{PROJECT_NAME}/project_plan.md")
  PLAN_MARKDOWN = PLAN_RESULT.content
  mcp__respec-ai__store_project_plan(
    project_name=PROJECT_NAME,
    project_plan_markdown=PLAN_MARKDOWN
  )
  Display: "✓ Loaded existing project plan from platform"
EXCEPT:
  Display: "No existing project plan found - will create new"
"""
        else:
            return """# Platform-specific sync not configured
Display: "⚠️ Sync not configured for this platform - continuing without sync"
"""


class BuildCommandTools(BaseModel):
    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_spec_tool: str = Field(..., description='Platform-specific tool for retrieving specs')
    comment_spec_tool: str = Field(..., description='Platform-specific tool for commenting on specs')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    @computed_field
    def get_spec_tool_interpolated(self) -> str:
        if '*' not in self.get_spec_tool:
            return self.get_spec_tool
        return self.get_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def comment_spec_tool_interpolated(self) -> str:
        if '*' not in self.comment_spec_tool:
            return self.comment_spec_tool
        return self.comment_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def sync_spec_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return """TRY:
  SPEC_MARKDOWN = Read(.respec-ai/projects/{PROJECT_NAME}/respec-specs/{SPEC_NAME}.md)
  mcp__respec-ai__store_spec(
    project_name=PROJECT_NAME,
    spec_name=SPEC_NAME,
    spec_markdown=SPEC_MARKDOWN
  )
  Display: "✓ Loaded spec '{SPEC_NAME}' from platform"
EXCEPT:
  Display: "No existing spec found in platform"
"""
        elif self.platform == PlatformType.LINEAR:
            return """TRY:
  SPEC_RESULT = mcp__linear-server__get_issue(spec_name=SPEC_NAME)
  SPEC_MARKDOWN = SPEC_RESULT.description
  mcp__respec-ai__store_spec(
    project_name=PROJECT_NAME,
    spec_name=SPEC_NAME,
    spec_markdown=SPEC_MARKDOWN
  )
  Display: "✓ Loaded spec '{SPEC_NAME}' from platform"
EXCEPT:
  Display: "No existing spec found in platform"
"""
        elif self.platform == PlatformType.GITHUB:
            return """TRY:
  SPEC_RESULT = mcp__github__get_issue(issue_title=SPEC_NAME)
  SPEC_MARKDOWN = SPEC_RESULT.body
  mcp__respec-ai__store_spec(
    project_name=PROJECT_NAME,
    spec_name=SPEC_NAME,
    spec_markdown=SPEC_MARKDOWN
  )
  Display: "✓ Loaded spec '{SPEC_NAME}' from platform"
EXCEPT:
  Display: "No existing spec found in platform"
"""
        else:
            return """# Platform-specific sync not configured
Display: "⚠️ Sync not configured for this platform - continuing without sync"
"""


class PlanRoadmapCommandTools(BaseModel):
    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_project_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    update_project_plan_tool: str = Field(..., description='Platform-specific tool for updating project plans')
    create_spec_tool: str = Field(..., description='Platform-specific tool for creating specs')
    get_spec_tool: str = Field(..., description='Platform-specific tool for retrieving specs')
    update_spec_tool: str = Field(..., description='Platform-specific tool for updating specs')
    list_project_specs_tool: str = Field(..., description='Platform-specific tool for listing project specs')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    @computed_field
    def get_project_plan_tool_interpolated(self) -> str:
        if '*' not in self.get_project_plan_tool:
            return self.get_project_plan_tool
        return self.get_project_plan_tool.replace('*', '{project_name}')

    @computed_field
    def update_project_plan_tool_interpolated(self) -> str:
        if '*' not in self.update_project_plan_tool:
            return self.update_project_plan_tool
        return self.update_project_plan_tool.replace('*', '{project_name}')

    @computed_field
    def create_spec_tool_interpolated(self) -> str:
        if '*' not in self.create_spec_tool:
            return self.create_spec_tool
        return self.create_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def get_spec_tool_interpolated(self) -> str:
        if '*' not in self.get_spec_tool:
            return self.get_spec_tool
        return self.get_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def update_spec_tool_interpolated(self) -> str:
        if '*' not in self.update_spec_tool:
            return self.update_spec_tool
        return self.update_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def list_project_specs_tool_interpolated(self) -> str:
        if '*' not in self.list_project_specs_tool:
            return self.list_project_specs_tool
        return self.list_project_specs_tool.replace('*', '{project_name}')

    @computed_field
    def sync_project_plan_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return """TRY:
  PLAN_MARKDOWN = Read(.respec-ai/projects/{PROJECT_NAME}/project_plan.md)
  mcp__respec-ai__store_project_plan(
    project_name=PROJECT_NAME,
    project_plan_markdown=PLAN_MARKDOWN
  )
  Display: "✓ Loaded project plan from platform"
EXCEPT:
  Display: "No existing project plan found"
"""
        elif self.platform == PlatformType.LINEAR:
            return """TRY:
  PLAN_RESULT = mcp__linear-server__get_document(project_name=PROJECT_NAME)
  PLAN_MARKDOWN = PLAN_RESULT.content
  mcp__respec-ai__store_project_plan(
    project_name=PROJECT_NAME,
    project_plan_markdown=PLAN_MARKDOWN
  )
  Display: "✓ Loaded project plan from platform"
EXCEPT:
  Display: "No existing project plan found"
"""
        elif self.platform == PlatformType.GITHUB:
            return """TRY:
  PLAN_RESULT = mcp__github__get_file(path=".respec-ai/projects/{PROJECT_NAME}/project_plan.md")
  PLAN_MARKDOWN = PLAN_RESULT.content
  mcp__respec-ai__store_project_plan(
    project_name=PROJECT_NAME,
    project_plan_markdown=PLAN_MARKDOWN
  )
  Display: "✓ Loaded project plan from platform"
EXCEPT:
  Display: "No existing project plan found"
"""
        else:
            return """# Platform-specific sync not configured
Display: "⚠️ Sync not configured for this platform"
"""

    @computed_field
    def sync_all_specs_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return """SPECS_LOADED = 0
SPEC_FILES = Glob(.respec-ai/projects/{PROJECT_NAME}/respec-specs/*.md)
FOR each spec_file in SPEC_FILES:
  SPEC_NAME = [extract filename without .md extension]
  SPEC_MARKDOWN = Read(spec_file)
  mcp__respec-ai__store_spec(
    project_name=PROJECT_NAME,
    spec_name=SPEC_NAME,
    spec_markdown=SPEC_MARKDOWN
  )
  SPECS_LOADED = SPECS_LOADED + 1
Display: "✓ Loaded {SPECS_LOADED} specs from platform"
"""
        elif self.platform == PlatformType.LINEAR:
            return """SPECS_LOADED = 0
SPEC_LIST = mcp__linear-server__list_issues(project_name=PROJECT_NAME, label="technical-specification")
FOR each spec in SPEC_LIST:
  SPEC_RESULT = mcp__linear-server__get_issue(issue_id=spec.id)
  SPEC_MARKDOWN = SPEC_RESULT.description
  SPEC_NAME = SPEC_RESULT.title
  mcp__respec-ai__store_spec(
    project_name=PROJECT_NAME,
    spec_name=SPEC_NAME,
    spec_markdown=SPEC_MARKDOWN
  )
  SPECS_LOADED = SPECS_LOADED + 1
Display: "✓ Loaded {SPECS_LOADED} specs from platform"
"""
        elif self.platform == PlatformType.GITHUB:
            return """SPECS_LOADED = 0
SPEC_LIST = mcp__github__list_issues(label="technical-specification")
FOR each spec in SPEC_LIST:
  SPEC_RESULT = mcp__github__get_issue(issue_number=spec.number)
  SPEC_MARKDOWN = SPEC_RESULT.body
  SPEC_NAME = SPEC_RESULT.title
  mcp__respec-ai__store_spec(
    project_name=PROJECT_NAME,
    spec_name=SPEC_NAME,
    spec_markdown=SPEC_MARKDOWN
  )
  SPECS_LOADED = SPECS_LOADED + 1
Display: "✓ Loaded {SPECS_LOADED} specs from platform"
"""
        else:
            return """# Platform-specific sync not configured
Display: "⚠️ Spec sync not configured for this platform"
"""


class PlanRoadmapAgentTools(BaseModel):
    create_spec_external: str = Field(..., description='Platform-specific tool for creating external specs')

    @computed_field
    def create_spec_tool_interpolated(self) -> str:
        if '*' not in self.create_spec_external:
            return self.create_spec_external
        return self.create_spec_external.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)


class SpecArchitectAgentTools(BaseModel):
    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')


class SpecCriticAgentTools(BaseModel):
    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    spec_length_soft_cap: int = Field(default=40000, description='Soft cap for spec length in characters')


class CreateSpecAgentTools(BaseModel):
    create_spec_tool: str = Field(..., description='Platform-specific tool for creating external specs')
    get_spec_tool: str = Field(..., description='Platform-specific tool for retrieving specs')
    update_spec_tool: str = Field(..., description='Platform-specific tool for updating specs')

    @computed_field
    def create_spec_tool_interpolated(self) -> str:
        if '*' not in self.create_spec_tool:
            return self.create_spec_tool
        # Markdown: Write(.respec-ai/projects/*/respec-specs/*.md)
        return self.create_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def get_spec_tool_interpolated(self) -> str:
        if '*' not in self.get_spec_tool:
            return self.get_spec_tool
        # Markdown: Read(.respec-ai/projects/*/respec-specs/*.md)
        return self.get_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)

    @computed_field
    def update_spec_tool_interpolated(self) -> str:
        if '*' not in self.update_spec_tool:
            return self.update_spec_tool
        # Markdown: Edit(.respec-ai/projects/*/respec-specs/*.md)
        return self.update_spec_tool.replace('*', '{project_name}', 1).replace('*', '{spec_name}', 1)


class BuildCoderAgentTools(BaseModel):
    update_task_status: str = Field(..., description='Platform-specific tool for updating task/issue status')

    @computed_field
    def update_task_tool_interpolated(self) -> str:
        if '*' not in self.update_task_status:
            return self.update_task_status
        # Unlikely to have wildcards for task status updates, but handle just in case
        return self.update_task_status.replace('*', '{project_name}', 1)
