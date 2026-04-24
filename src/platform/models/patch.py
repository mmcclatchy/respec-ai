from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import Field, PrivateAttr, computed_field

from ..adapters import PlatformAdapter, get_platform_adapter
from ..platform_selector import PlatformType
from ..tool_doc_extractor import ToolDocumentationExtractor
from ..tool_doc_generator import ToolDocGenerator
from ..tool_enums import BuiltInToolCapability, RespecAITool
from .core import AgentToolsModel, CommandToolsModel


class PatchCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.CONSOLIDATE_REVIEW_CYCLE,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.STORE_USER_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
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
    consolidate_review_cycle: str = Field(..., description='Consolidate structured reviewer results for an iteration')

    # Standards loop (Phase 2)
    initialize_standards_loop: str = Field(..., description='Initialize Phase 2 standards loop')
    decide_standards_action: str = Field(..., description='Decide Phase 2 standards loop action')
    get_standards_feedback: str = Field(..., description='Get feedback from Phase 2 standards loop')

    # Feedback
    store_user_feedback: str = Field(..., description='Store user feedback')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')

    # Task operations
    get_task_document: str = Field(..., description='Get task document')
    store_task_document: str = Field(..., description='Store amendment task document')

    # Agent invocations
    invoke_patch_planner: str = Field(..., description='Invocation text for respec-patch-planner agent')
    invoke_task_plan_critic: str = Field(..., description='Invocation text for respec-task-plan-critic agent')
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
    roadmap_command_invocation: str = Field(..., description='Invocation text to hand off to respec-roadmap command')
    phase_command_invocation: str = Field(..., description='Invocation text to hand off to respec-phase command')

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


class PatchPlannerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GREP, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_phase: str = Field(..., description='Retrieve Phase document via get_document')
    retrieve_task: str = Field(..., description='Retrieve existing task document via get_document')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for refinement')
    store_task: str = Field(..., description='Store amendment task via store_document')
    link_loop: str = Field(..., description='Link loop to task document after storing')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
