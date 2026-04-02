"""Pydantic models for platform configuration with fail-fast validation."""

from pathlib import Path
from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field, field_validator

from .adapters import PlatformAdapter, get_platform_adapter
from .platform_selector import PlatformType
from .tool_doc_extractor import ToolDocumentationExtractor
from .tool_doc_generator import ToolDocGenerator
from .tool_enums import (
    BuiltInTool,
    RespecAICommand,
    RespecAITool,
    ToolEnums,
)
from .tui_adapters.base import TuiAdapter


class AgentToolsModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tui_adapter: TuiAdapter = Field(..., description='TUI adapter for model resolution')


class CommandToolsModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tui_adapter: TuiAdapter = Field(..., description='TUI adapter for platform-specific rendering')


class PlatformModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        extra='forbid',  # Fail if unexpected fields provided
    )


class ProjectStack(PlatformModel):
    language: str | None = Field(default=None, description='Primary language (e.g., python, javascript, go, rust)')
    backend_framework: str | None = Field(
        default=None, description='Backend framework (e.g., fastapi, fastmcp, flask, django, express)'
    )
    frontend_framework: str | None = Field(
        default=None, description='Frontend framework (e.g., react, next, vue, svelte)'
    )
    package_manager: str | None = Field(default=None, description='Package manager (e.g., uv, pip, npm, yarn)')
    runtime_version: str | None = Field(default=None, description='Language runtime version (e.g., 3.13, 22)')
    database: str | None = Field(default=None, description='Database (e.g., postgresql, sqlite, mongodb, neo4j)')
    api_style: str | None = Field(default=None, description='API style (e.g., rest, graphql, grpc, mcp)')
    async_runtime: bool | None = Field(default=None, description='Async runtime (True for async/await patterns)')
    type_checker: str | None = Field(default=None, description='Type checker (e.g., ty, mypy, pyright for Python)')
    css_framework: str | None = Field(default=None, description='CSS framework (e.g., tailwindcss, bootstrap)')
    ui_components: str | None = Field(default=None, description='UI component library (e.g., daisyui, shadcn)')
    architecture: str | None = Field(default=None, description='Architecture pattern (e.g., monolith, microservices)')


class LanguageTooling(PlatformModel):
    test_runner: str = Field(description='Test runner name (e.g., pytest, vitest)')
    test_command: str = Field(description='Command to run tests')
    coverage_command: str = Field(description='Command to run tests with coverage')
    checker: str = Field(description='Static checker name (e.g., mypy, tsc, cargo check)')
    check_command: str = Field(description='Command to run static checks')
    linter: str = Field(description='Linter name (e.g., ruff, eslint, clippy)')
    lint_command: str = Field(description='Command to run linter')


class ProjectToolingConfig(PlatformModel):
    tooling: dict[str, LanguageTooling] = Field(
        default_factory=dict,
        description='Language-keyed tooling configuration',
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


class PlanSetupRequest(PlatformRequest):
    platform: PlatformType = Field(description='Platform to use for this project')
    requirements: PlatformRequirements = Field(description='Platform requirements that must be met')


class PlanSetupWithRecommendationRequest(PlatformRequest):
    requirements: PlatformRequirements = Field(description='Platform requirements for recommendation')


class PlanPlatformChangeRequest(PlatformRequest):
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


class PhaseCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.GET_DOCUMENT,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_phase_tool: str = Field(..., description='Platform-specific tool for creating phases')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    update_phase_tool: str = Field(..., description='Platform-specific tool for updating phases')
    platform: PlatformType = Field(..., description='Selected platform type')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')

    # Agent invocations
    invoke_phase_architect: str = Field(..., description='Invocation text for respec-phase-architect agent')
    invoke_phase_critic: str = Field(..., description='Invocation text for respec-phase-critic agent')
    task_command_invocation: str = Field(..., description='Invocation text to hand off to respec-task command')

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
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_tool:
            return self.create_phase_tool
        return self.create_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        return self.get_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def update_phase_tool_interpolated(self) -> str:
        if '*' not in self.update_phase_tool:
            return self.update_phase_tool
        return self.update_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def sync_plan_instructions(self) -> str:
        return self._adapter.plan_sync_instructions

    @computed_field
    def sync_phase_instructions(self) -> str:
        return self._adapter.phase_sync_instructions

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
            'store_plan',
            'get_plan_markdown',
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

    @computed_field
    def config_location(self) -> str:
        return self._adapter.config_location

    @computed_field
    def phase_discovery_pattern(self) -> str:
        return self._adapter.phase_discovery_pattern

    @computed_field
    def phase_discovery_instructions(self) -> str:
        return self._adapter.phase_discovery_instructions

    @computed_field
    def phase_resource_pattern(self) -> str:
        return self._adapter.phase_resource_pattern

    @computed_field
    def phase_resource_example(self) -> str:
        return self._adapter.phase_resource_example

    @computed_field
    def phase_location_hint(self) -> str:
        return self._adapter.phase_location_hint

    @computed_field
    def discovery_tool_invocation(self) -> str:
        return self._adapter.discovery_tool_invocation


class PlanCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.STORE_CURRENT_ANALYSIS,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.GET_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_project_external: str = Field(..., description='Platform-specific tool for creating external project')
    get_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    platform: PlatformType = Field(..., description='Selected platform type')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')

    # Parameterized MCP tool invocations
    initialize_plan_loop: str = Field(..., description='Initialize plan quality loop')
    initialize_analyst_loop: str = Field(..., description='Initialize analyst refinement loop')
    store_plan: str = Field(..., description='Store strategic plan in MCP')
    store_plan_in_loop: str = Field(..., description='Store plan in analyst loop')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Retrieve previous analyst analysis')
    decide_loop_action: str = Field(..., description='Decide next loop action')
    store_user_feedback: str = Field(..., description='Store user feedback during plan refinement')

    # Agent and command invocations
    invoke_plan_critic: str = Field(..., description='Invocation text for respec-plan-critic agent')
    invoke_plan_analyst: str = Field(..., description='Invocation text for respec-plan-analyst agent')
    invoke_analyst_critic: str = Field(..., description='Invocation text for respec-analyst-critic agent')
    conversation_invocation: str = Field(..., description='Invocation text for plan-conversation workflow')
    conversation_workflow_name: str = Field(..., description='Platform-appropriate name for the conversation workflow')
    roadmap_command_invocation: str = Field(..., description='Invocation text for roadmap workflow handoff')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def create_project_tool_interpolated(self) -> str:
        if '*' not in self.create_project_external:
            return self.create_project_external
        return self.create_project_external.replace('*', '{plan_name}')

    @computed_field
    def get_plan_tool_interpolated(self) -> str:
        if '*' not in self.get_plan_tool:
            return self.get_plan_tool
        return self.get_plan_tool.replace('*', '{plan_name}')

    @computed_field
    def sync_plan_instructions(self) -> str:
        return self._adapter.plan_sync_instructions

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'store_plan',
            'get_plan_markdown',
            'get_previous_analysis',
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
    def config_location(self) -> str:
        return self._adapter.config_location

    @computed_field
    def plan_resource_example(self) -> str:
        return self._adapter.plan_resource_example


class CodeCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.GET_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    comment_phase_tool: str = Field(..., description='Platform-specific tool for commenting on phases')
    platform: PlatformType = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    store_document: str = Field(..., description='Store task build plan')
    store_phase_document: str = Field(..., description='Store phase specification in MCP')
    get_phase_document: str = Field(..., description='Get phase specification')
    initialize_planning_loop: str = Field(..., description='Initialize planning loop')
    initialize_coding_loop: str = Field(..., description='Initialize coding loop')
    initialize_standards_loop: str = Field(..., description='Initialize Phase 2 standards loop')
    decide_planning_action: str = Field(..., description='Decide planning loop action')
    decide_coding_action: str = Field(..., description='Decide coding loop action')
    decide_standards_action: str = Field(..., description='Decide Phase 2 standards loop action')
    get_standards_feedback: str = Field(..., description='Get feedback from Phase 2 standards loop')
    store_user_feedback: str = Field(..., description='Store user feedback')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_task_document: str = Field(..., description='Get task document')

    # Agent invocations
    invoke_coder: str = Field(..., description='Invocation text for respec-coder agent (Phase 1)')
    invoke_quality_checker: str = Field(..., description='Invocation text for respec-automated-quality-checker agent')
    invoke_spec_alignment: str = Field(..., description='Invocation text for respec-spec-alignment-reviewer agent')
    invoke_code_quality: str = Field(..., description='Invocation text for respec-code-quality-reviewer agent')
    invoke_dynamic_reviewer_pattern: str = Field(..., description='Invocation pattern for dynamic specialist reviewers')
    invoke_consolidator: str = Field(..., description='Invocation text for respec-review-consolidator agent')
    invoke_coder_standards: str = Field(
        ..., description='Invocation text for respec-coder agent (Phase 2 standards-only)'
    )
    invoke_coding_standards_reviewer: str = Field(
        ..., description='Invocation text for respec-coding-standards-reviewer agent'
    )

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        return self.get_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def comment_phase_tool_interpolated(self) -> str:
        if '*' not in self.comment_phase_tool:
            return self.comment_phase_tool
        return self.comment_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def sync_phase_instructions(self) -> str:
        return self._adapter.phase_sync_instructions

    @computed_field
    def phase_glob_pattern(self) -> str:
        return self._adapter.phase_discovery_instructions

    @computed_field
    def phase_discovery_instructions(self) -> str:
        return self._adapter.phase_discovery_instructions

    @computed_field
    def phase_location_hint(self) -> str:
        return self._adapter.phase_location_hint

    @computed_field
    def config_directory(self) -> str:
        return self._adapter.config_directory

    @computed_field
    def research_directory_pattern(self) -> str:
        return '.best-practices/*.md'

    @computed_field
    def research_example_path(self) -> str:
        return '.best-practices/htmx-patterns-codegen.md'

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


class PatchCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.GET_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    platform: PlatformType = Field(..., description='Selected platform type')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')

    # Phase operations
    store_phase_document: str = Field(..., description='Store phase specification in MCP')
    get_phase_document: str = Field(..., description='Get phase specification')
    update_phase_document: str = Field(..., description='Update phase document')

    # Planning loop
    initialize_planning_loop: str = Field(..., description='Initialize planning loop')
    link_planning_loop: str = Field(..., description='Link planning loop to phase document')
    decide_planning_action: str = Field(..., description='Decide planning loop action')

    # Coding loop (Phase 1)
    initialize_coding_loop: str = Field(..., description='Initialize coding loop')
    decide_coding_action: str = Field(..., description='Decide coding loop action')

    # Standards loop (Phase 2)
    initialize_standards_loop: str = Field(..., description='Initialize Phase 2 standards loop')
    decide_standards_action: str = Field(..., description='Decide Phase 2 standards loop action')
    get_standards_feedback: str = Field(..., description='Get feedback from Phase 2 standards loop')

    # Feedback
    store_user_feedback: str = Field(..., description='Store user feedback')
    get_feedback: str = Field(..., description='Get latest feedback')

    # Task operations
    get_task_document: str = Field(..., description='Get task document')
    store_task_document: str = Field(..., description='Store amendment task document')

    # Agent invocations
    invoke_patch_planner: str = Field(..., description='Invocation text for respec-patch-planner agent')
    invoke_task_plan_critic: str = Field(..., description='Invocation text for respec-task-plan-critic agent')
    invoke_coder: str = Field(..., description='Invocation text for respec-coder agent (Phase 1)')
    invoke_quality_checker: str = Field(..., description='Invocation text for respec-automated-quality-checker agent')
    invoke_spec_alignment: str = Field(..., description='Invocation text for respec-spec-alignment-reviewer agent')
    invoke_dynamic_reviewer_pattern: str = Field(..., description='Invocation pattern for dynamic specialist reviewers')
    invoke_consolidator: str = Field(..., description='Invocation text for respec-review-consolidator agent')
    invoke_coder_standards: str = Field(
        ..., description='Invocation text for respec-coder agent (Phase 2 standards-only)'
    )
    invoke_coding_standards_reviewer: str = Field(
        ..., description='Invocation text for respec-coding-standards-reviewer agent'
    )

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def sync_phase_instructions(self) -> str:
        return self._adapter.phase_sync_instructions

    @computed_field
    def config_directory(self) -> str:
        return self._adapter.config_directory

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'store_document',
            'get_document',
            'update_document',
            'link_loop_to_document',
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

    @computed_field
    def link_loop_to_document_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('link_loop_to_document')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''

    @computed_field
    def task_resource_pattern(self) -> str:
        return self._adapter.task_resource_pattern

    @computed_field
    def task_location_setup(self) -> str:
        return self._adapter.task_location_setup

    @computed_field
    def list_all_phases(self) -> str:
        return self._adapter.list_phases_tool


class PlanRoadmapCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.ASK_USER_QUESTION, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    list_project_phases_tool: str = Field(..., description='Platform-specific tool for listing project phases')
    platform: PlatformType = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    get_plan: str = Field(..., description='Get strategic plan')
    initialize_loop: str = Field(..., description='Initialize roadmap loop')
    create_roadmap: str = Field(..., description='Create roadmap in MCP')
    decide_loop_action: str = Field(..., description='Decide loop action')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_roadmap: str = Field(..., description='Get final roadmap')

    # Agent invocations
    invoke_roadmap_agent: str = Field(..., description='Invocation text for respec-roadmap agent')
    invoke_roadmap_critic: str = Field(..., description='Invocation text for respec-roadmap-critic agent')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def get_plan_tool_interpolated(self) -> str:
        if '*' not in self.get_plan_tool:
            return self.get_plan_tool
        return self.get_plan_tool.replace('*', '{plan_name}')

    @computed_field
    def list_project_phases_tool_interpolated(self) -> str:
        if '*' not in self.list_project_phases_tool:
            return self.list_project_phases_tool
        return self.list_project_phases_tool.replace('*', '{plan_name}')

    @computed_field
    def sync_plan_instructions(self) -> str:
        return self._adapter.plan_sync_instructions

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'get_feedback',
            'get_plan_markdown',
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


class TaskCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.ASK_USER_QUESTION, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.READ, '.respec-ai/plans/*/phases/*.md'),
        (BuiltInTool.TASK, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_phase_tool: str = Field(..., description='Platform-specific tool for retrieving phases')
    list_phase_tasks_tool: str = Field(..., description='Platform-specific tool for listing tasks')
    platform: PlatformType = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    store_phase_document: str = Field(..., description='Store phase document in MCP')
    initialize_loop: str = Field(..., description='Initialize task planning loop')
    link_loop: str = Field(..., description='Link loop to phase document')
    decide_loop_action: str = Field(..., description='Decide loop action')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_task: str = Field(..., description='Get Task document')
    store_user_feedback: str = Field(..., description='Store user feedback')

    # Agent invocations
    invoke_task_planner: str = Field(..., description='Invocation text for respec-task-planner agent')
    invoke_task_plan_critic: str = Field(..., description='Invocation text for respec-task-plan-critic agent')

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        return self.get_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def list_phase_tasks_tool_interpolated(self) -> str:
        """Interpolate task listing tool path.

        Tasks are stored flat under phases/tasks/ (not nested per phase).
        Only plan_name wildcard needs replacement.
        """
        if '*' not in self.list_phase_tasks_tool:
            return self.list_phase_tasks_tool
        return self.list_phase_tasks_tool.replace('*', '{plan_name}', 1)

    @computed_field
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = [
            'initialize_refinement_loop',
            'decide_loop_next_action',
            'get_feedback',
            'store_user_feedback',
            'get_document',
            'store_document',
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
    def link_loop_to_document_inline_doc(self) -> str:
        if not self._tool_extractor:
            return ''
        try:
            doc = self._tool_extractor.get_tool_documentation('link_loop_to_document')
            return ToolDocGenerator.generate_inline_doc(doc)
        except Exception:
            return ''

    @computed_field
    def task_resource_pattern(self) -> str:
        return self._adapter.task_resource_pattern

    @computed_field
    def task_location_setup(self) -> str:
        return self._adapter.task_location_setup

    @computed_field
    def phase_discovery_instructions(self) -> str:
        return self._adapter.phase_discovery_instructions

    @computed_field
    def phase_location_hint(self) -> str:
        return self._adapter.phase_location_hint

    @computed_field
    def sync_phase_instructions(self) -> str:
        return self._adapter.phase_sync_instructions


class PlanRoadmapAgentTools(BaseModel):
    create_phase_external: str = Field(..., description='Platform-specific tool for creating external phases')

    @computed_field
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_external:
            return self.create_phase_external
        return self.create_phase_external.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)


class PhaseArchitectAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.BASH, ''),
        (BuiltInTool.GREP, ''),
        (BuiltInTool.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback')
    get_document: str = Field(..., description='Retrieve current specification')
    update_document: str = Field(..., description='Store complete specification')


class PhaseCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    phase_length_soft_cap: int = Field(default=40000, description='Soft cap for phase length in characters')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_document: str = Field(..., description='Retrieve specification via loop_id')
    store_feedback: str = Field(..., description='Store critic feedback')


class CreatePhaseAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
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
    platform: PlatformType = Field(..., description='Selected platform type')

    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @computed_field
    def create_phase_tool_interpolated(self) -> str:
        if '*' not in self.create_phase_tool:
            return self.create_phase_tool
        # Markdown: Write using PathComponent pattern
        return self.create_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def get_phase_tool_interpolated(self) -> str:
        if '*' not in self.get_phase_tool:
            return self.get_phase_tool
        # Markdown: Read using PathComponent pattern
        return self.get_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def update_phase_tool_interpolated(self) -> str:
        if '*' not in self.update_phase_tool:
            return self.update_phase_tool
        # Markdown: Edit using PathComponent pattern
        return self.update_phase_tool.replace('*', '{plan_name}', 1).replace('*', '{phase_name}', 1)

    @computed_field
    def platform_tool_documentation(self) -> str:
        return self._adapter.platform_tool_documentation


class CoderAgentTools(AgentToolsModel):
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
        return self.update_task_status.replace('*', '{plan_name}', 1)

    @computed_field
    def research_directory_pattern(self) -> str:
        return '.best-practices/*.md'

    @computed_field
    def research_example_path(self) -> str:
        return '.best-practices/htmx-patterns-codegen.md'


class AnalystCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.STORE_CURRENT_ANALYSIS,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Get previous analysis iteration')
    store_current_analysis: str = Field(..., description='Store current analysis results')


class PlanAnalystAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.STORE_CURRENT_ANALYSIS,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Get previous analysis iteration')
    store_current_analysis: str = Field(..., description='Store current analysis results')


class PlanCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')


class RoadmapAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,  # For plan retrieval
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.CREATE_ROADMAP,  # Dedicated roadmap creation
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback')
    create_roadmap: str = Field(..., description='Store roadmap to MCP')


class RoadmapCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_ROADMAP,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_roadmap: str = Field(..., description='Retrieve roadmap from MCP')
    store_feedback: str = Field(..., description='Store critic feedback')


class AutomatedQualityCheckerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
        (BuiltInTool.GREP, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_review_section: str = Field(..., description='Store quality check review section')


class SpecAlignmentReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_review_section: str = Field(..., description='Store spec alignment review section')


class CodeQualityReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.GREP, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_review_section: str = Field(..., description='Store code quality review section')

    @computed_field
    def research_directory_pattern(self) -> str:
        return '.best-practices/*.md'


class FrontendReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_review_section: str = Field(..., description='Store frontend review section')


class BackendApiReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_review_section: str = Field(..., description='Store backend API review section')


class DatabaseReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_review_section: str = Field(..., description='Store database review section')


class InfrastructureReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_review_section: str = Field(..., description='Store infrastructure review section')


class CodingStandardsReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEW_SECTION,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_review_section: str = Field(..., description='Store coding standards review section (Phase 1)')
    store_feedback: str = Field(..., description='Store CriticFeedback directly (Phase 2 mode)')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')


class ReviewConsolidatorAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_REVIEW_SECTION,
        RespecAITool.LIST_REVIEW_SECTIONS,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_review_sections: str = Field(..., description='List review section documents')
    get_review_section: str = Field(..., description='Get individual review section document')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_feedback: str = Field(..., description='Store consolidated CriticFeedback')


class TaskPlannerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, '.best-practices/*.md'),
        (BuiltInTool.GREP, ''),
        (BuiltInTool.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_phase: str = Field(..., description='Retrieve Phase document via get_document')
    retrieve_task: str = Field(..., description='Retrieve task breakdown document via get_document')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for refinement')
    store_task: str = Field(..., description='Store task breakdown via store_document')
    link_loop: str = Field(..., description='Link loop to task document after storing')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')


class TaskPlanCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve task breakdown document via get_document')
    retrieve_phase: str = Field(..., description='Retrieve Phase document via get_document')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_feedback: str = Field(..., description='Store critic feedback via store_critic_feedback')


class PatchPlannerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, ''),
        (BuiltInTool.GREP, ''),
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_phase: str = Field(..., description='Retrieve Phase document via get_document')
    retrieve_task: str = Field(..., description='Retrieve existing task document via get_document')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for refinement')
    store_task: str = Field(..., description='Store amendment task via store_document')
    link_loop: str = Field(..., description='Link loop to task document after storing')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
