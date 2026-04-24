from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import Field, PrivateAttr, computed_field

from ..adapters import PlatformAdapter, get_platform_adapter
from ..platform_selector import PlatformType
from ..tool_doc_extractor import ToolDocumentationExtractor
from ..tool_doc_generator import ToolDocGenerator
from ..tool_enums import BuiltInToolCapability, RespecAITool
from .core import AgentToolsModel, CommandToolsModel


class CodeCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.CONSOLIDATE_REVIEW_CYCLE,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
        RespecAITool.GET_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    platform: PlatformType = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    store_document: str = Field(..., description='Store task build plan')
    store_phase_document: str = Field(..., description='Store phase specification in MCP')
    get_phase_document: str = Field(..., description='Get phase specification')
    initialize_coding_loop: str = Field(..., description='Initialize coding loop')
    initialize_task_loop: str = Field(..., description='Initialize task retrieval loop for the selected task')
    initialize_standards_loop: str = Field(..., description='Initialize Phase 2 standards loop')
    decide_coding_action: str = Field(..., description='Decide coding loop action')
    decide_standards_action: str = Field(..., description='Decide Phase 2 standards loop action')
    consolidate_review_cycle: str = Field(..., description='Consolidate structured reviewer results for an iteration')
    get_standards_feedback: str = Field(..., description='Get feedback from Phase 2 standards loop')
    store_user_feedback: str = Field(..., description='Store user feedback')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_task_document: str = Field(..., description='Get task document through task-linked loop retrieval')
    get_task_document_by_key: str = Field(..., description='Get task document by explicit task key')
    list_task_documents: str = Field(..., description='List task documents under a phase')
    link_task_loop: str = Field(..., description='Link task retrieval loop to selected task document')

    # Agent invocations
    invoke_coder: str = Field(..., description='Invocation text for respec-coder agent (Phase 1)')
    commit_command_invocation: str = Field(..., description='Invocation text for respec-commit command')
    invoke_quality_checker: str = Field(..., description='Invocation text for respec-automated-quality-checker agent')
    invoke_spec_alignment: str = Field(..., description='Invocation text for respec-spec-alignment-reviewer agent')
    invoke_code_quality: str = Field(..., description='Invocation text for respec-code-quality-reviewer agent')
    invoke_dynamic_reviewer_pattern: str = Field(..., description='Invocation pattern for dynamic specialist reviewers')
    phase1_review_parallel_policy: str = Field(
        ..., description='Adapter-rendered parallel orchestration policy for Phase 1 reviewer fan-out'
    )
    invoke_coder_standards: str = Field(
        ..., description='Invocation text for respec-coder agent (Phase 2 standards-only)'
    )
    invoke_coding_standards_reviewer: str = Field(
        ..., description='Invocation text for respec-coding-standards-reviewer agent'
    )
    task_command_invocation: str = Field(..., description='Invocation text to hand off to respec-task command')
    phase_command_invocation: str = Field(..., description='Invocation text to hand off to respec-phase command')
    code_command_invocation: str = Field(..., description='Invocation text to hand off to respec-code command')

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


class CoderAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.WRITE, ''),
        (BuiltInToolCapability.EDIT, ''),
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
        (BuiltInToolCapability.TODO_WRITE, ''),
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


class CommitCommandTools(CommandToolsModel):
    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for command allowed-tools section')


class AutomatedQualityCheckerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
        (BuiltInToolCapability.GREP, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store quality check reviewer result')


class SpecAlignmentReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store spec alignment reviewer result')


class CodeQualityReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.GREP, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store code quality reviewer result')

    @computed_field
    def research_directory_pattern(self) -> str:
        return '.best-practices/*.md'


class FrontendReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_reviewer_result: str = Field(..., description='Store frontend reviewer result')


class BackendApiReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_reviewer_result: str = Field(..., description='Store backend API reviewer result')


class DatabaseReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_reviewer_result: str = Field(..., description='Store database reviewer result')


class InfrastructureReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_reviewer_result: str = Field(..., description='Store infrastructure reviewer result')


class CodingStandardsReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve Task document from planning loop')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_reviewer_result: str = Field(..., description='Store coding standards reviewer result')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
