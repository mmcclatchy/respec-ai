from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import Field, PrivateAttr, computed_field

from ..adapters import PlatformAdapter, get_platform_adapter
from ..platform_selector import PlatformType
from ..tool_doc_extractor import ToolDocumentationExtractor
from ..tool_doc_generator import ToolDocGenerator
from ..tool_enums import BuiltInTool, RespecAITool
from .core import AgentToolsModel, CommandToolsModel


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
        (BuiltInTool.GLOB, ''),
        (BuiltInTool.READ, '.respec-ai/plans/*/phases/*.md'),
        (BuiltInTool.TASK, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
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
    task_command_reference: str = Field(..., description='Adapter-rendered reference text for respec-task command')
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
        (BuiltInTool.READ, '.respec-ai/plans/*/references/*.md'),
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

    builtin_tools: ClassVar[list[tuple[BuiltInTool, str]]] = [
        (BuiltInTool.READ, '.respec-ai/plans/*/references/*.md'),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_task: str = Field(..., description='Retrieve task breakdown document via get_document')
    retrieve_phase: str = Field(..., description='Retrieve Phase document via get_document')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_feedback: str = Field(..., description='Store critic feedback via store_critic_feedback')
