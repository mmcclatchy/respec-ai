from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import Field, PrivateAttr, computed_field

from ..adapters import PlatformAdapter, get_platform_adapter
from ..platform_selector import PlatformType
from ..tool_doc_extractor import ToolDocumentationExtractor
from ..tool_doc_generator import ToolDocGenerator
from ..tool_enums import BuiltInToolCapability, RespecAITool
from .core import AgentToolsModel, CommandToolsModel


class PlanRoadmapCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        # Step 4's user_input gate stores the user's choice; without this grant that instruction
        # names a tool the command cannot call.
        RespecAITool.STORE_USER_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    get_plan_tool: str = Field(..., description='Platform-specific tool for retrieving project plans')
    list_project_phases_tool: str = Field(..., description='Platform-specific tool for listing project phases')
    platform: PlatformType = Field(..., description='Selected platform type')
    nested_orchestration: bool = Field(
        default=False,
        description='True when the adapter supports nested subagents and the loop lives in respec-roadmap-orchestrator',
    )

    # Parameterized MCP tool invocations
    get_plan: str = Field(..., description='Get strategic plan')
    initialize_loop: str = Field(..., description='Initialize roadmap loop')
    create_roadmap: str = Field(..., description='Create roadmap in MCP')
    get_loop_status: str = Field(..., description='Get roadmap loop status for iteration check')
    decide_loop_action: str = Field(..., description='Decide loop action')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_roadmap: str = Field(..., description='Get final roadmap')
    store_user_feedback: str = Field(..., description='Store the user decision from the quality gate')

    # Agent invocations
    invoke_roadmap_orchestrator: str = Field(
        default='', description='Invocation text for respec-roadmap-orchestrator (nested-capable adapters only)'
    )
    invoke_roadmap_agent: str = Field(..., description='Invocation text for respec-roadmap agent')
    invoke_roadmap_critic: str = Field(..., description='Invocation text for respec-roadmap-critic agent')
    phase_extraction_parallel_policy: str = Field(
        ..., description='Adapter-rendered parallel orchestration policy for create-phase fan-out'
    )
    plan_command_invocation: str = Field(..., description='Invocation text to hand off to respec-plan command')
    phase_command_invocation: str = Field(..., description='Invocation text to hand off to respec-phase command')

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
    def mcp_tools_reference(self) -> str:
        if not self._tool_extractor:
            return ''

        tool_names = (
            ['get_feedback', 'store_user_feedback', 'get_plan_markdown']
            if self.nested_orchestration
            else [
                'initialize_refinement_loop',
                'decide_loop_next_action',
                'get_feedback',
                'get_plan_markdown',
                'create_roadmap',
                'get_roadmap',
            ]
        )

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


class CreatePhaseAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.STORE_DOCUMENT,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.UPDATE_DOCUMENT,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    create_phase_tool: str = Field(..., description='Platform-specific tool for creating external phases')
    get_phase: str = Field(
        ...,
        description=(
            'Retrieve the single sparse phase already stored by respec-roadmap during roadmap '
            'creation, without pulling the full roadmap markdown for every other phase'
        ),
    )
    store_document: str = Field(..., description='Store phase in MCP storage')
    platform: PlatformType = Field(..., description='Selected platform type')

    _adapter: PlatformAdapter = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._adapter = get_platform_adapter(self.platform)

    @computed_field
    def platform_tool_documentation(self) -> str:
        return self._adapter.platform_tool_documentation


class RoadmapAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,  # For plan retrieval
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.CREATE_ROADMAP,  # Dedicated roadmap creation
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, '.respec-ai/plans/*/references/*.md'),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    plans_dir: str = Field(..., description='TUI-specific plans directory path')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_loop_status: str = Field(..., description='Get loop status for iteration check')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback')
    create_roadmap: str = Field(..., description='Store roadmap to MCP')


class RoadmapOrchestratorAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_LOOP_STATUS,
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, '.respec-ai/plans/*/references/*.md'),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    list_project_phases_tool: str = Field(..., description='Platform-specific tool for listing project phases')

    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    initialize_loop: str = Field(..., description='Initialize roadmap loop')
    get_loop_status: str = Field(..., description='Get roadmap loop status for iteration check')
    decide_loop_action: str = Field(..., description='Decide loop action')
    get_feedback: str = Field(..., description='Get latest feedback')
    get_roadmap: str = Field(..., description='Get final roadmap')

    invoke_roadmap_agent: str = Field(..., description='Invocation text for respec-roadmap agent')
    invoke_roadmap_critic: str = Field(..., description='Invocation text for respec-roadmap-critic agent')
    invoke_create_phase: str = Field(..., description='Invocation text for respec-create-phase agent')
    phase_extraction_parallel_policy: str = Field(
        ..., description='Adapter-rendered parallel orchestration policy for create-phase fan-out'
    )


class RoadmapCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.GET_ROADMAP,
        RespecAITool.LIST_DOCUMENTS,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, '.respec-ai/plans/*/references/*.md'),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_feedback: str = Field(..., description='Retrieve prior critic feedback')
    get_roadmap: str = Field(..., description='Retrieve roadmap from MCP')
    get_roadmap_metadata: str = Field(..., description='Retrieve roadmap metadata without phase bodies')
    list_phases: str = Field(..., description='List phase keys for the plan')
    get_phase: str = Field(..., description='Retrieve a single phase by plan/phase key')
    store_feedback: str = Field(..., description='Store critic feedback')
