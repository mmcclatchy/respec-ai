from typing import Any, ClassVar

from fastmcp import FastMCP
from pydantic import Field, PrivateAttr, computed_field

from ..adapters import PlatformAdapter, get_platform_adapter
from ..platform_selector import PlatformType
from ..tool_doc_extractor import ToolDocumentationExtractor
from ..tool_doc_generator import ToolDocGenerator
from ..tool_enums import BuiltInToolCapability, RespecAICommand, RespecAITool
from .core import AgentToolsModel, CommandToolsModel


class PlanCommandTools(CommandToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.INITIALIZE_REFINEMENT_LOOP,
        RespecAITool.DECIDE_LOOP_NEXT_ACTION,
        RespecAITool.GET_LOOP_STATUS,
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
    get_loop_status: str = Field(..., description='Retrieve current analyst loop status')
    get_previous_analysis: str = Field(..., description='Retrieve previous analyst analysis')
    get_feedback: str = Field(..., description='Retrieve prior critic feedback for analyst loop display')
    decide_loop_action: str = Field(..., description='Decide next loop action')
    store_user_feedback: str = Field(..., description='Store user feedback during plan refinement')

    # Agent and command invocations
    invoke_plan_critic: str = Field(..., description='Invocation text for respec-plan-critic agent')
    invoke_plan_analyst: str = Field(..., description='Invocation text for respec-plan-analyst agent')
    invoke_analyst_critic: str = Field(..., description='Invocation text for respec-analyst-critic agent')
    conversation_invocation: str = Field(..., description='Invocation text for plan-conversation workflow')
    conversation_workflow_name: str = Field(..., description='Platform-appropriate name for the conversation workflow')
    roadmap_command_invocation: str = Field(..., description='Invocation text for roadmap workflow handoff')
    phase_command_invocation: str = Field(..., description='Invocation text for phase workflow handoff')

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


class PlanConversationCommandTools(CommandToolsModel):
    plan_command_invocation: str = Field(
        default='', description='Adapter-rendered invocation for strategic planning workflow'
    )
    plan_command_name: str = Field(default='', description='Name of the strategic planning command/skill')
    plan_conversation_command_name: str = Field(
        default='', description='Name of the conversation workflow command/skill'
    )

    def model_post_init(self, __context: Any) -> None:
        self.plan_command_name = RespecAICommand.PLAN.value
        self.plan_conversation_command_name = RespecAICommand.PLAN_CONVERSATION.value
        self.plan_command_invocation = self.tui_adapter.render_command_invocation(
            self.plan_command_name,
            '[plan-name] [optional: initial context]',
            '',
            requires_user_interaction=False,
        )


class StandardsCommandTools(CommandToolsModel):
    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    standards_command_name: str = Field(default='', description='Name of the standards workflow command/skill')
    ask_user_question_tool_name: str = Field(
        default='',
        description='Adapter-specific interactive prompt tool name (empty when unsupported)',
    )
    target_argument_hint: str = Field(
        default='[language|all]',
        description='Argument hint adjusted by adapter interactive prompt capability',
    )
    missing_target_resolution_text: str = Field(
        default='',
        description='Workflow instructions for handling missing language targets',
    )

    def model_post_init(self, __context: Any) -> None:
        self.standards_command_name = RespecAICommand.STANDARDS.value
        ask_tool_name = self.tui_adapter.ask_user_question_tool_name
        if ask_tool_name:
            self.ask_user_question_tool_name = ask_tool_name
            self.target_argument_hint = '[optional: language|all]'
            self.missing_target_resolution_text = (
                f'IF TARGET is missing:\n'
                '  If AVAILABLE_LANGUAGES has exactly one entry:\n'
                '    TARGET = that single language\n'
                '    Emit info: "No target provided; auto-selected single available language: {TARGET}."\n'
                '  Else:\n'
                f'    MUST call {ask_tool_name} to select one language or "all".\n'
                f'    {ask_tool_name}:\n'
                '      Header: "Standards Target"\n'
                '      Question: "Select standards target language or all."\n'
                '      Options:\n'
                '        1) one language (pick from AVAILABLE_LANGUAGES)\n'
                '        2) all languages\n'
                '    TARGET = selected value\n'
                '\n'
                f'If {ask_tool_name} is unavailable:\n'
                '  Stop and return structured error:\n'
                f'  "standards_target_selection_unavailable: missing {ask_tool_name} tool; cannot continue without '
                'explicit target selection."'
            )
        else:
            self.ask_user_question_tool_name = ''
            self.target_argument_hint = '[language|all]'
            self.missing_target_resolution_text = (
                'IF TARGET is missing:\n'
                '  If AVAILABLE_LANGUAGES has exactly one entry:\n'
                '    TARGET = that single language\n'
                '    Emit info: "No target provided; auto-selected single available language: {TARGET}."\n'
                '  Else:\n'
                '    Stop and return structured error:\n'
                '    "standards_target_required: explicit target required on this TUI."\n'
                '    Present numbered options for selection:\n'
                '      1..N) one entry per AVAILABLE_LANGUAGES item (in deterministic sorted order)\n'
                '      N+1) all\n'
                '    Include exact rerun commands beside each option:\n'
                '      - respec-standards <language>\n'
                '      - respec-standards all\n'
                '    Do not continue rendering until user reruns with an explicit target.'
            )


class AnalystCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CRITIC_FEEDBACK,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Get previous analysis iteration')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback iterations')
    store_feedback: str = Field(..., description='Store current critic feedback')


class PlanAnalystAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_PREVIOUS_ANALYSIS,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_CURRENT_ANALYSIS,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
    get_previous_analysis: str = Field(..., description='Get previous analysis iteration')
    get_feedback: str = Field(..., description='Retrieve previous critic feedback iterations')
    store_current_analysis: str = Field(..., description='Store current analysis results')


class PlanCriticAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = []

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    get_plan: str = Field(..., description='Retrieve strategic plan from MCP')
