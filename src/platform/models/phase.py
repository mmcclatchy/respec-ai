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
        RespecAITool.VALIDATE_DOCUMENT,
        RespecAITool.LINK_LOOP_TO_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.STORE_USER_FEEDBACK,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    create_phase_tool: str = Field(..., description='Platform-specific tool for creating phases')
    platform: PlatformType = Field(..., description='Selected platform type')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')

    code_command_invocation: str = Field(..., description='Invocation text to hand off to respec-code command')
    invoke_architect_explore: str = Field(..., description='Fresh respec-phase-architect invocation in explore mode')
    invoke_architect_draft: str = Field(..., description='Fresh respec-phase-architect invocation in draft mode')
    invoke_architect_revise: str = Field(..., description='Fresh respec-phase-architect invocation in revise mode')
    resume_architect: str = Field(
        ...,
        description=(
            'Resume of the recorded architect in ARCHITECT_MODE; empty where the TUI cannot resume a subagent'
        ),
    )
    invoke_critic_review: str = Field(..., description='respec-phase-critic invocation in review mode')
    invoke_bp_pipeline: str = Field(..., description='bp-pipeline dispatch for one approved research proposal')
    bp_preflight_command: str = Field(..., description='Shell command whose exit code reports bp availability')
    store_document_user_edit: str = Field(
        ..., description='Store a hand-edited phase document with the frozen-field exception'
    )

    store_document: str = Field(..., description='Store the phase document, stage marker included')
    initialize_loop: str = Field(..., description="Initialize the run's review loop")
    link_loop: str = Field(..., description='Link the review loop to the phase document')
    get_loop_status: str = Field(..., description='Get review loop status')
    decide_loop_action: str = Field(..., description='Decide the next action from the latest critic review')
    get_feedback: str = Field(..., description='Get the latest critic review and every user feedback entry')
    get_document: str = Field(..., description='Get the current phase document through the review loop')
    store_user_feedback: str = Field(..., description='Store round-tagged user feedback')
    validate_document: str = Field(..., description='Check candidate content for silent parser loss')
    validate_document_structure: str = Field(
        ..., description='Check the stored phase document for structural findings, in key mode'
    )

    _tool_extractor: ClassVar[ToolDocumentationExtractor | None] = None
    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @classmethod
    def initialize_tool_docs(cls, mcp: FastMCP) -> None:
        cls._tool_extractor = ToolDocumentationExtractor(mcp)

    @computed_field
    def sync_plan_instructions(self) -> str:
        return self._adapter.plan_sync_instructions

    @computed_field
    def sync_phase_instructions(self) -> str:
        return self._adapter.phase_sync_instructions

    @computed_field
    def phase_location_setup(self) -> str:
        return self._adapter.phase_location_setup

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
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CURRENT_ANALYSIS,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.VALIDATE_DOCUMENT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.BASH, ''),
        (BuiltInToolCapability.GREP, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.WRITE, '.respec-ai/plans/*/phases/*/implementation.md'),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')
    get_feedback: str = Field(..., description='Retrieve the latest critic review and every user entry')
    get_document: str = Field(..., description='Retrieve current specification')
    update_document: str = Field(..., description='Store complete specification')
    store_analysis: str = Field(..., description='Replace the loop notes slot with the complete notes')
    get_analysis: str = Field(..., description='Read the loop notes slot')
    validate_document: str = Field(
        ..., description='Check the stored phase document and the implementation.md body, in key mode'
    )


class PhaseCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
        RespecAITool.VALIDATE_DOCUMENT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_document: str = Field(..., description='Retrieve specification via loop_id')
    get_feedback: str = Field(..., description='Retrieve prior critic reviews and every user entry')
    store_feedback: str = Field(..., description='Store critic feedback')
    validate_document: str = Field(
        ..., description='Check the stored phase document and the implementation.md body, in key mode'
    )
