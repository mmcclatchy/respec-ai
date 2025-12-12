"""Pydantic models for platform configuration with fail-fast validation."""

from pathlib import Path
from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from .path_constants import PathComponent
from .platform_selector import PlatformType
from .tool_doc_extractor import ToolDocumentationExtractor
from .tool_doc_generator import ToolDocGenerator
from .tool_enums import (
    AbstractOperation,
    BuiltInTool,
    ExternalPlatformTool,
    RespecAICommand,
    RespecAITool,
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
    command_name: RespecAICommand = Field(description='Name of the command template to generate')


class ProjectConfig(PlatformRequest):
    platform: PlatformType = Field(description='Platform configured for this project')
    requirements: PlatformRequirements = Field(description='Platform requirements for this project')
    config_data: dict[str, Any] = Field(default_factory=dict, description='Additional configuration data')


class ToolReference(PlatformModel):
    tool: ToolEnums = Field(description='The specific tool to reference')
    parameters: str = Field(default='', description='Tool parameters like path patterns or agent names')

    def render(self) -> str:
        if self.parameters:
            return f'{self.tool}({self.parameters})'
        return self.tool

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
                raise ValueError(f'File operation tool {tool} requires non-empty path parameter')
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
            if not v.tool.startswith('mcp__linear-server__'):
                raise ValueError(f'Linear platform tool must be a Linear server tool, got: {v.tool}')
        return v

    @field_validator('github_tool')
    @classmethod
    def validate_github_tool(cls, v: ToolReference | None) -> ToolReference | None:
        if v and isinstance(v.tool, ExternalPlatformTool):
            if not v.tool.startswith('mcp__github__'):
                raise ValueError(f'GitHub platform tool must be a GitHub tool, got: {v.tool}')
        return v

    @field_validator('markdown_tool')
    @classmethod
    def validate_markdown_tool(cls, v: ToolReference | None) -> ToolReference | None:
        if v and not isinstance(v.tool, BuiltInTool):
            raise ValueError(f'Markdown platform must use built-in tools, got: {v.tool}')
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


class PhaseCommandTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.STORE_PROJECT_PLAN,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.GET_DOCUMENT,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_phase_tool: str = Field(..., description='Platform-specific tool for creating phases')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    update_phase_tool: str = Field(..., description='Platform-specific tool for updating phases')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    store_plan: str = Field(..., description='Store strategic plan')
    store_document: str = Field(..., description='Store phase document')
    initialize_loop: str = Field(..., description='Initialize refinement loop')
    get_plan: str = Field(..., description='Retrieve strategic plan')
    link_loop: str = Field(..., description='Link loop to document')
    get_loop_status: str = Field(..., description='Get loop status')
    decide_loop_action: str = Field(..., description='Decide loop action')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_document: str = Field(..., description='Get final phase document')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_tool:
            return self.create_phase_tool
        return self.create_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        return self.get_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def update_phase_tool_interpolated(self) -> str:
        if '*' not in self.update_phase_tool:
            return self.update_phase_tool
        return self.update_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def sync_project_plan_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return f"""PLAN_MARKDOWN = Read({PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PLAN_NAME}}/{PathComponent.PROJECT_PLAN_FILE})
mcp__respec-ai__store_project_plan(project_name=PLAN_NAME, project_plan_markdown=PLAN_MARKDOWN)"""
        elif self.platform == PlatformType.LINEAR:
            return """PLAN_RESULT = mcp__linear-server__get_document(project_name=PLAN_NAME)
mcp__respec-ai__store_project_plan(project_name=PLAN_NAME, project_plan_markdown=PLAN_RESULT.content)"""
        elif self.platform == PlatformType.GITHUB:
            return f"""PLAN_RESULT = mcp__github__get_file(path="{PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PLAN_NAME}}/{PathComponent.PROJECT_PLAN_FILE}")
mcp__respec-ai__store_project_plan(project_name=PLAN_NAME, project_plan_markdown=PLAN_RESULT.content)"""
        else:
            return """# Platform sync not configured"""

    @computed_field
    def sync_phase_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return f"""PHASE_MARKDOWN = Read({PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PHASES_DIR}/{{PHASE_NAME}}.md)
mcp__respec-ai__store_document(doc_type="phase", path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}", content=PHASE_MARKDOWN)"""
        elif self.platform == PlatformType.LINEAR:
            return """PHASE_RESULT = mcp__linear-server__get_issue(phase_name=PHASE_NAME)
mcp__respec-ai__store_document(doc_type="phase", path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}", content=PHASE_RESULT.description)"""
        elif self.platform == PlatformType.GITHUB:
            return """PHASE_RESULT = mcp__github__get_issue(issue_title=PHASE_NAME)
mcp__respec-ai__store_document(doc_type="phase", path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}", content=PHASE_RESULT.body)"""
        else:
            return """# Platform sync not configured"""

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'store_document',
            'get_document',
            'link_loop_to_document',
            'get_loop_status',
            'get_feedback',
            'store_project_plan',
            'get_project_plan_markdown',
        ]

        try:
            tool_docs = [self._tool_extractor.get_tool_documentation(name) for name in tool_names]
            return ToolDocGenerator.generate_reference_section(tool_docs)
        except Exception:
            return ''

    @computed_field
    def initialize_refinement_loop_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('initialize_refinement_loop')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''

    @computed_field
    def store_document_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('store_document')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''

    @computed_field
    def link_loop_to_document_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('link_loop_to_document')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''


class PlanCommandTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.STORE_CURRENT_ANALYSIS,
        RespecAITool.STORE_PROJECT_PLAN,
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.CREATE_PLAN_COMPLETION_REPORT,
        RespecAITool.STORE_PLAN_COMPLETION_REPORT,
        RespecAITool.GET_PLAN_COMPLETION_REPORT_MARKDOWN,
        RespecAITool.UPDATE_PLAN_COMPLETION_REPORT,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_project_external: str = Field(..., description='Platform-specific tool for creating external project')
    create_project_completion_external: str = Field(
        ..., description='Platform-specific tool for creating external project completion'
    )
    get_project_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    initialize_analyst_loop: str = Field(..., description='Initialize analyst refinement loop')
    store_plan: str = Field(..., description='Store strategic plan in MCP')
    store_plan_in_loop: str = Field(..., description='Store plan in analyst loop')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Retrieve previous analyst analysis')
    decide_loop_action: str = Field(..., description='Decide next loop action')
    store_completion_report: str = Field(..., description='Store plan completion report')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

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
            return f"""TRY:
  PLAN_MARKDOWN = Read({PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PROJECT_PLAN_FILE})
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
            return f"""TRY:
  PLAN_RESULT = mcp__github__get_file(path="{PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PROJECT_PLAN_FILE}")
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

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'store_project_plan',
            'get_project_plan_markdown',
            'get_previous_analysis',
            'store_plan_completion_report',
        ]

        try:
            tool_docs = [self._tool_extractor.get_tool_documentation(name) for name in tool_names]
            return ToolDocGenerator.generate_reference_section(tool_docs)
        except Exception:
            return ''

    @computed_field
    def initialize_refinement_loop_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('initialize_refinement_loop')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''


class CodeCommandTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.GET_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    comment_phase_tool: str = Field(..., description='Platform-specific tool for commenting on phases')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    store_document: str = Field(..., description='Store task build plan')
    store_phase_document: str = Field(..., description='Store phase specification in MCP')
    get_phase_document: str = Field(..., description='Get phase specification')
    initialize_planning_loop: str = Field(..., description='Initialize planning loop')
    initialize_coding_loop: str = Field(..., description='Initialize coding loop')
    decide_planning_action: str = Field(..., description='Decide planning loop action')
    decide_coding_action: str = Field(..., description='Decide coding loop action')
    store_user_feedback: str = Field(..., description='Store user feedback')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_task_document: str = Field(..., description='Get task document')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        return self.get_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def comment_phase_tool_interpolated(self) -> str:
        if '*' not in self.comment_phase_tool:
            return self.comment_phase_tool
        return self.comment_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def sync_phase_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return f"""TRY:
  PHASE_MARKDOWN = Read({PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PHASES_DIR}/{{PHASE_NAME}}.md)
  mcp__respec-ai__store_document(
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  Display: "✓ Loaded phase '{{PHASE_NAME}}' from platform"
EXCEPT:
  Display: "No existing phase found in platform"
"""
        elif self.platform == PlatformType.LINEAR:
            return """TRY:
  PHASE_RESULT = mcp__linear-server__get_issue(phase_name=PHASE_NAME)
  PHASE_MARKDOWN = PHASE_RESULT.description
  mcp__respec-ai__store_document(
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  Display: "✓ Loaded phase '{PHASE_NAME}' from platform"
EXCEPT:
  Display: "No existing phase found in platform"
"""
        elif self.platform == PlatformType.GITHUB:
            return """TRY:
  PHASE_RESULT = mcp__github__get_issue(issue_title=PHASE_NAME)
  PHASE_MARKDOWN = PHASE_RESULT.body
  mcp__respec-ai__store_document(
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  Display: "✓ Loaded phase '{PHASE_NAME}' from platform"
EXCEPT:
  Display: "No existing phase found in platform"
"""
        else:
            return """# Platform-specific sync not configured
Display: "⚠️ Sync not configured for this platform - continuing without sync"
"""

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'store_document',
            'get_document',
            'store_user_feedback',
            'get_feedback',
        ]

        try:
            tool_docs = [self._tool_extractor.get_tool_documentation(name) for name in tool_names]
            return ToolDocGenerator.generate_reference_section(tool_docs)
        except Exception:
            return ''

    @computed_field
    def initialize_refinement_loop_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('initialize_refinement_loop')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''


class PlanRoadmapCommandTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.CREATE_ROADMAP,
        RespecAITool.GET_ROADMAP,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
        RespecAITool.GET_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_project_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    update_project_plan_tool: str = Field(..., description='Platform-specific tool for updating project plans')
    create_phase_tool: str = Field(..., description='Platform-specific tool for creating phases')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    update_phase_tool: str = Field(..., description='Platform-specific tool for updating phases')
    list_project_phases_tool: str = Field(..., description='Platform-specific tool for listing project phases')
    platform: 'PlatformType' = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    get_plan: str = Field(..., description='Get strategic plan')
    initialize_loop: str = Field(..., description='Initialize roadmap loop')
    create_roadmap: str = Field(..., description='Create roadmap in MCP')
    decide_loop_action: str = Field(..., description='Decide loop action')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_roadmap: str = Field(..., description='Get final roadmap')
    list_documents: str = Field(..., description='List stored phase documents')
    get_document: str = Field(..., description='Get phase document')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

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
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_tool:
            return self.create_phase_tool
        return self.create_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        return self.get_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def update_phase_tool_interpolated(self) -> str:
        if '*' not in self.update_phase_tool:
            return self.update_phase_tool
        return self.update_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def list_project_phases_tool_interpolated(self) -> str:
        if '*' not in self.list_project_phases_tool:
            return self.list_project_phases_tool
        return self.list_project_phases_tool.replace('*', '{project_name}')

    @computed_field
    def sync_project_plan_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return f"""TRY:
  PLAN_MARKDOWN = Read({PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PROJECT_PLAN_FILE})
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
            return f"""TRY:
  PLAN_RESULT = mcp__github__get_file(path="{PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PROJECT_PLAN_FILE}")
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
    def sync_all_phases_instructions(self) -> str:
        if self.platform == PlatformType.MARKDOWN:
            return f"""PHASES_LOADED = 0
PHASE_FILES = Glob({PathComponent.RESPEC_AI_DIR}/{PathComponent.PLANS_DIR}/{{PROJECT_NAME}}/{PathComponent.PHASES_DIR}/*.md)
FOR each phase_file in PHASE_FILES:
  PHASE_NAME = [extract filename without .md extension]
  PHASE_MARKDOWN = Read(phase_file)
  mcp__respec-ai__store_document(
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  PHASES_LOADED = PHASES_LOADED + 1
Display: "✓ Loaded {{PHASES_LOADED}} phases from platform"
"""
        elif self.platform == PlatformType.LINEAR:
            return """PHASES_LOADED = 0
PHASE_LIST = mcp__linear-server__list_issues(project_name=PROJECT_NAME, label="phase")
FOR each phase in PHASE_LIST:
  PHASE_RESULT = mcp__linear-server__get_issue(issue_id=phase.id)
  PHASE_MARKDOWN = PHASE_RESULT.description
  PHASE_NAME = PHASE_RESULT.title
  mcp__respec-ai__store_document(
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  PHASES_LOADED = PHASES_LOADED + 1
Display: "✓ Loaded {PHASES_LOADED} phases from platform"
"""
        elif self.platform == PlatformType.GITHUB:
            return """PHASES_LOADED = 0
PHASE_LIST = mcp__github__list_issues(label="phase")
FOR each phase in PHASE_LIST:
  PHASE_RESULT = mcp__github__get_issue(issue_number=phase.number)
  PHASE_MARKDOWN = PHASE_RESULT.body
  PHASE_NAME = PHASE_RESULT.title
  mcp__respec-ai__store_document(
    doc_type="phase",
    path=f"{{PROJECT_NAME}}/{{PHASE_NAME}}",
    content=PHASE_MARKDOWN
  )
  PHASES_LOADED = PHASES_LOADED + 1
Display: "✓ Loaded {PHASES_LOADED} phases from platform"
"""
        else:
            return """# Platform-specific sync not configured
Display: "⚠️ Phase sync not configured for this platform"
"""

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'get_feedback',
            'get_project_plan_markdown',
            'create_roadmap',
            'get_roadmap',
        ]

        try:
            tool_docs = [self._tool_extractor.get_tool_documentation(name) for name in tool_names]
            return ToolDocGenerator.generate_reference_section(tool_docs)
        except Exception:
            return ''

    @computed_field
    def initialize_refinement_loop_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('initialize_refinement_loop')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''


class PlanRoadmapAgentTools(BaseModel):
    create_phase_external: str = Field(..., description='Platform-specific tool for creating external phases')

    @computed_field
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_external:
            return self.create_phase_external
        return self.create_phase_external.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)


class PhaseArchitectAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.BASH, '~/.claude/scripts/research-advisor-archive-scan.sh:*'),
        (BuiltInTool.GREP, ''),
        (BuiltInTool.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback')
    get_document: str = Field(..., description='Retrieve current specification')
    update_document: str = Field(..., description='Store complete specification')


class PhaseCriticAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    phase_length_soft_cap: int = Field(default=40000, description='Soft cap for phase length in characters')
    get_document: str = Field(..., description='Retrieve specification via loop_id')
    store_feedback: str = Field(..., description='Store critic feedback')


class CreatePhaseAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_ROADMAP,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    create_phase_tool: str = Field(..., description='Platform-specific tool for creating external phases')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    update_phase_tool: str = Field(..., description='Platform-specific tool for updating phases')
    get_roadmap: str = Field(..., description='Retrieve complete roadmap from MCP')
    store_document: str = Field(..., description='Store phase in MCP storage')

    @computed_field
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_tool:
            return self.create_phase_tool
        # Markdown: Write using PathComponent pattern
        return self.create_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        # Markdown: Read using PathComponent pattern
        return self.get_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def update_phase_tool_interpolated(self) -> str:
        if '*' not in self.update_phase_tool:
            return self.update_phase_tool
        # Markdown: Edit using PathComponent pattern
        return self.update_phase_tool.replace('*', '{project_name}', 1).replace('*', '{phase_name}', 1)


class TaskCoderAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.WRITE, ''),
        (BuiltInTool.EDIT, ''),
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
        (BuiltInTool.TODO_WRITE, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    update_task_status: str = Field(..., description='Platform-specific tool for updating task/issue status')
    retrieve_task: str = Field(..., description='Retrieve build plan document')
    retrieve_phase: str = Field(..., description='Retrieve phase specification')
    retrieve_feedback: str = Field(..., description='Retrieve all feedback from coding loop')

    @computed_field
    def update_task_tool_interpolated(self) -> str:
        if '*' not in self.update_task_status:
            return self.update_task_status
        # Unlikely to have wildcards for task status updates, but handle just in case
        return self.update_task_status.replace('*', '{project_name}', 1)


class AnalystCriticAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.STORE_CURRENT_ANALYSIS,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_project_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Get previous analysis iteration')
    store_current_analysis: str = Field(..., description='Store current analysis results')


class PlanAnalystAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.STORE_CURRENT_ANALYSIS,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_project_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Get previous analysis iteration')
    store_current_analysis: str = Field(..., description='Store current analysis results')


class PlanCriticAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_project_plan: str = Field(..., description='Retrieve strategic plan from MCP')


class RoadmapAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_PROJECT_PLAN_MARKDOWN,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_project_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback')


class RoadmapCriticAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_ROADMAP,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_roadmap: str = Field(..., description='Retrieve roadmap from MCP')
    store_feedback: str = Field(..., description='Store critic feedback')


class TaskCriticAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Phase document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_feedback: str = Field(..., description='Store critic feedback in planning loop')


class TaskReviewerAgentTools(BaseModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Phase document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_feedback: str = Field(..., description='Store code review feedback in coding loop')
