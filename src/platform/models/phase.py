from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import Field, PrivateAttr, computed_field

from ..adapters import PlatformAdapter, get_platform_adapter
from ..platform_selector import PlatformType
from ..tool_doc_extractor import ToolDocumentationExtractor
from ..tool_doc_generator import ToolDocGenerator
from ..tool_enums import BuiltInToolCapability, RespecAITool
from .core import AgentToolsModel, CommandToolsModel


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
    platform: PlatformType = Field(..., description='Selected platform type')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')

    # Agent invocations
    invoke_phase_architect: str = Field(..., description='Invocation text for respec-phase-architect agent')
    invoke_phase_critic: str = Field(..., description='Invocation text for respec-phase-critic agent')
    invoke_phase_critic_post_synthesis: str = Field(
        ..., description='Invocation text for post-synthesis respec-phase-critic validation'
    )
    task_command_invocation: str = Field(..., description='Invocation text to hand off to respec-task command')
    phase_command_reference: str = Field(..., description='Adapter-rendered reference text for respec-phase command')
    roadmap_command_invocation: str = Field(..., description='Invocation text to hand off to respec-roadmap command')
    plan_command_invocation: str = Field(..., description='Invocation text to hand off to respec-plan command')
    code_command_invocation: str = Field(..., description='Invocation text to hand off to respec-code command')

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


class PhaseArchitectAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.BASH, ''),
        (BuiltInToolCapability.GREP, ''),
        (BuiltInToolCapability.GLOB, ''),
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

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    phase_length_soft_cap: int = Field(default=40000, description='Soft cap for phase length in characters')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_document: str = Field(..., description='Retrieve specification via loop_id')
    get_feedback: str = Field(..., description='Retrieve prior critic feedback')
    store_feedback: str = Field(..., description='Store critic feedback')
