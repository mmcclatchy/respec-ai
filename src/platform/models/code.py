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
        RespecAITool.GET_REVIEWER_FEEDBACK_CONTEXT,
        RespecAITool.GET_REVIEW_SECTION,
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for allowed-tools section')
    platform: PlatformType = Field(..., description='Selected platform type')

    # Parameterized MCP tool invocations
    store_phase_document: str = Field(..., description='Store phase specification in MCP')
    get_phase_document: str = Field(..., description='Get phase specification')
    initialize_coding_loop: str = Field(..., description='Initialize coding loop')
    initialize_phase_loop: str = Field(..., description='Initialize phase-type loop for phase document linking')
    initialize_standards_loop: str = Field(..., description='Initialize Phase 2 standards loop')
    decide_coding_action: str = Field(..., description='Decide coding loop action')
    decide_standards_action: str = Field(..., description='Decide Phase 2 standards loop action')
    consolidate_review_cycle: str = Field(..., description='Consolidate structured reviewer results for an iteration')
    get_standards_feedback: str = Field(..., description='Get feedback from Phase 2 standards loop')
    get_reviewer_feedback_context: str = Field(..., description='Get curated active-reviewer feedback context')
    store_user_feedback: str = Field(..., description='Store user feedback')
    get_feedback: str = Field(..., description='Get latest feedback')
    link_phase_loop: str = Field(..., description='Link phase loop to phase document')
    get_design_conformance_write_back: str = Field(
        ..., description='Retrieve the design-conformance-reviewer write-back section via get_review_section'
    )

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
    def phase_resource_pattern(self) -> str:
        return self._adapter.phase_resource_pattern

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
        RespecAITool.GET_REVIEWER_RESULT,
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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build ordering')
    retrieve_phase: str = Field(..., description='Retrieve phase specification')
    retrieve_feedback: str = Field(..., description='Retrieve all feedback from coding loop')

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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store quality check reviewer result')


class DesignConformanceReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
        RespecAITool.STORE_REVIEW_SECTION,
    ]

    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback (coder handoff Deviations) for context')
    store_reviewer_result: str = Field(..., description='Store design-conformance reviewer result')
    store_write_back: str = Field(
        ..., description='Store the confirmed-legitimate write-back payload via store_review_section'
    )


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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store code quality reviewer result')

    @computed_field
    def research_directory_pattern(self) -> str:
        return '.best-practices/*.md'


class FrontendReviewerAgentTools(AgentToolsModel):
    respec_ai_tools: ClassVar[list[RespecAITool]] = [
        RespecAITool.GET_DOCUMENT,
        RespecAITool.GET_FEEDBACK,
        RespecAITool.STORE_REVIEWER_RESULT,
    ]

    # No WRITE (F19 -- the MCP server writes screenshots/traces, the agent never does) and no
    # BASH_OUTPUT (F17 -- opencode.py maps it to None and TemplateToolBuilder.build() raises on
    # that, which would break `respec-ai regenerate` for OpenCode outright). BASH is for
    # `respec-ai frontend-preflight` only, never for starting servers or running builds directly.
    builtin_tools: ClassVar[list[tuple[BuiltInToolCapability, str]]] = [
        (BuiltInToolCapability.READ, ''),
        (BuiltInToolCapability.GLOB, ''),
        (BuiltInToolCapability.BASH, ''),
    ]

    # Playwright MCP tool grants, passed through TemplateToolBuilder.add_platform_tools as
    # verbatim strings (F20) -- the same escape hatch already used for Linear/GitHub tools,
    # bypassing the RespecAITool enum deliberately scoped to respec-ai's own server. Optional at
    # runtime: when the server isn't registered the reviewer degrades to source-only evidence
    # (F10) rather than failing on an unresolvable tool.
    #
    # Verified against the real, currently-published @playwright/mcp server (queried its live
    # `tools/list` response directly -- see phase-7 doc's "Contract wording" note) rather than
    # trusting the design-time tool names: there is no `browser_verify_*` tool family and no
    # `browser_set_storage_state` tool in the published server. Storage state is a server
    # *startup* flag (`--storage-state <path>`), applied at Playwright MCP registration time
    # (docs/CLI_GUIDE.md), not a per-call tool grant -- so it is correctly absent here.
    # `browser_run_code_unsafe` is excluded deliberately (decisions.md, phase-7 scope);
    # `browser_network_request` (singular) is included alongside the plural list tool because
    # seam review needs a single request's full body/headers, which the plural tool does not
    # return.
    browser_tools: ClassVar[list[str]] = [
        f'mcp__playwright__{tool}'
        for tool in (
            'browser_navigate',
            'browser_snapshot',
            'browser_click',
            'browser_hover',
            'browser_type',
            'browser_fill_form',
            'browser_select_option',
            'browser_press_key',
            'browser_wait_for',
            'browser_resize',
            'browser_evaluate',
            'browser_console_messages',
            'browser_network_requests',
            'browser_network_request',
            'browser_take_screenshot',
            'browser_close',
        )
    ]

    tools_yaml: str = Field(..., description='Rendered YAML for agent tools section')
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store frontend reviewer result')


class BackendApiReviewerAgentTools(AgentToolsModel):
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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store backend API reviewer result')


class DatabaseReviewerAgentTools(AgentToolsModel):
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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
    store_reviewer_result: str = Field(..., description='Store database reviewer result')


class InfrastructureReviewerAgentTools(AgentToolsModel):
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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
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
    retrieve_implementation_plan: str = Field(..., description='Read implementation.md for build context')
    retrieve_phase: str = Field(..., description='Retrieve Phase document by project and phase name')
    store_reviewer_result: str = Field(..., description='Store coding standards reviewer result')
    retrieve_feedback: str = Field(..., description='Retrieve previous feedback for progress tracking')
