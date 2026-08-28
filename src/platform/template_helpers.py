from .tui_adapters.claude_code import ClaudeCodeAdapter as _ClaudeCodeAdapter
from .models import (
    AnalystCriticAgentTools,
    AutomatedQualityCheckerAgentTools,
    BackendApiReviewerAgentTools,
    CodeCommandTools,
    CommitCommandTools,
    CoderAgentTools,
    CodeQualityReviewerAgentTools,
    CodingStandardsReviewerAgentTools,
    CreatePhaseAgentTools,
    DatabaseReviewerAgentTools,
    DesignConformanceReviewerAgentTools,
    DesignSyncCommandTools,
    FrontendReviewerAgentTools,
    InfrastructureReviewerAgentTools,
    PatchCommandTools,
    PatchPlannerAgentTools,
    PhaseArchitectAgentTools,
    PhaseCommandTools,
    PhaseCriticAgentTools,
    PlanAnalystAgentTools,
    PlanCommandTools,
    PlanConversationCommandTools,
    PlanCriticAgentTools,
    PlanRoadmapCommandTools,
    RoadmapAgentTools,
    RoadmapCriticAgentTools,
    SpecAlignmentReviewerAgentTools,
    StandardsCommandTools,
    ToolReference,
)
from .adapters import get_platform_adapter
from .platform_selector import PlatformType
from .tool_doc_generator import ToolDocGenerator
from .tool_enums import BuiltInToolCapability, RespecAIAgent, RespecAITool
from .tui_adapters.base import TuiAdapter


class TemplateToolBuilder:
    def __init__(self, tui_adapter: TuiAdapter) -> None:
        # NOTE FOR MAINTAINERS:
        # Shared platform code stores built-in tools as semantic capabilities.
        # This builder is the rendering boundary that converts those
        # capabilities into adapter-specific runtime tool names. Do not emit
        # raw adapter runtime names directly from shared code paths.
        self.tui_adapter = tui_adapter
        self.tools: list[ToolReference] = []

    def add_task_agent(self, agent_name: RespecAIAgent) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInToolCapability.TASK, parameters=agent_name))
        return self

    def add_bash_script(self, script_path: str) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInToolCapability.BASH, parameters=script_path))
        return self

    def add_respec_ai_tool(self, tool: RespecAITool) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=tool))
        return self

    def add_builtin_tool(self, tool: BuiltInToolCapability, parameters: str = '') -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=tool, parameters=parameters))
        return self

    def add_optional_builtin_tool(self, tool: BuiltInToolCapability, parameters: str = '') -> 'TemplateToolBuilder':
        """Grant a built-in capability only where the adapter supports it, skipping it elsewhere.

        Unlike `add_builtin_tool`, an adapter mapping the capability to `None` is not an
        error here -- it is how a tiered capability (F32) degrades per-TUI without raising.
        """
        if self.tui_adapter.render_builtin_tool_name(tool) is None:
            return self
        return self.add_builtin_tool(tool, parameters)

    def add_platform_tools(self, platform_tools: list[str]) -> 'TemplateToolBuilder':
        for tool_string in platform_tools:
            # For platform tools, we don't validate the enum since they're already processed
            # Just store them as plain strings in the final tools list
            self.tools.append(
                ToolReference(tool=BuiltInToolCapability.TASK, parameters=f'__PLATFORM_TOOL__{tool_string}')
            )
        return self

    def build(self) -> list[str]:
        tool_strings = []
        for tool_ref in self.tools:
            if tool_ref.tool == BuiltInToolCapability.TASK and tool_ref.parameters.startswith('__PLATFORM_TOOL__'):
                tool_strings.append(tool_ref.parameters[len('__PLATFORM_TOOL__') :])
                continue

            if isinstance(tool_ref.tool, BuiltInToolCapability):
                runtime_name = self.tui_adapter.render_builtin_tool_name(tool_ref.tool)
                if runtime_name is None:
                    raise ValueError(
                        f'{self.tui_adapter.__class__.__name__} does not support built-in tool capability '
                        f'{tool_ref.tool}'
                    )
                if tool_ref.parameters:
                    tool_strings.append(f'{runtime_name}({tool_ref.parameters})')
                else:
                    tool_strings.append(runtime_name)
                continue

            tool_strings.append(tool_ref.render())
        return tool_strings

    def render_yaml_tools(self, indent: str = '  ') -> str:
        tool_strings = self.build()
        return '\n'.join(f'{indent}- {tool}' for tool in tool_strings)

    def render_comma_separated_tools(self) -> str:
        tool_strings = self.build()
        return ', '.join(tool_strings)


def _add_adapter_question_tool(builder: TemplateToolBuilder, adapter: TuiAdapter) -> None:
    if adapter.ask_user_question_tool_name:
        builder.add_builtin_tool(BuiltInToolCapability.ASK_USER_QUESTION)


PLAN_CONVERSATION_INLINE_GUIDE = """\
As the primary agent, conduct conversational requirements gathering directly with the user.

PACING: Ask 1-2 questions per message. Wait for the user to respond before continuing.
Do NOT present all questions at once. Cover topics through genuine back-and-forth conversation.
Spend multiple turns on a topic if it's rich — depth matters more than covering every bullet.
Move on when the user gives short, confident answers or you can summarize their position back to them.

Stage 1: Vision and Context Discovery
- Start with: "Tell me about what you're building — what problem are you trying to solve?"
- Follow up on their answer before introducing new topics
- Cover: what's driving the project, what success looks like, who's involved

Stage 2: Progressive Requirement Refinement
- Explore scope, user experience, integrations, and constraints through follow-up

Stage 3: Detail and Validation
- Validate your understanding, clarify priorities and timeline

Stage 4: Technology Stack Discussion
- Languages, frameworks, databases, deployment — present options when the user is uncertain

Stage 5: Architecture Direction
- Component structure, integrations, data flow — establish direction, not detailed design

Stage 6: Scope Boundaries and Risk Assessment
- Anti-requirements, performance targets, risks, quality bar

Compile all gathered information into CONVERSATION_CONTEXT variable using structured markdown.\
"""


def _resolve_tui_adapter(tui_adapter: 'TuiAdapter | None') -> 'TuiAdapter':
    return tui_adapter if tui_adapter is not None else _ClaudeCodeAdapter()


def create_phase_command_tools(
    create_phase_tool: str,
    phase_retrieval_tool: str,
    phase_listing_tool: str,
    platform_type: 'PlatformType',
    plans_dir: str = '~/.claude/plans',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PhaseCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
    builder.add_task_agent(RespecAIAgent.PHASE_CRITIC)
    builder.add_builtin_tool(BuiltInToolCapability.TASK, 'bp')
    builder.add_builtin_tool(BuiltInToolCapability.BASH, '')

    for tool in PhaseCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_builtin_tool(BuiltInToolCapability.READ, '')
    # Covers phase.md (Steps 8-9 edit gate) and the two named skeleton-materialization
    # scratch files (Step 11.5: .skeleton-index.md, .test-list.md) -- never source paths;
    # those are written create-only by the `materialize-skeletons` CLI command via Bash.
    builder.add_builtin_tool(BuiltInToolCapability.WRITE, '.respec-ai/plans/*/phases/*/*.md')
    # Step 4.5 discovers .respec-ai/config/standards/*.toml to assemble
    # PROJECT_CONFIG_CONTEXT_MARKDOWN for the architect (F8).
    builder.add_builtin_tool(BuiltInToolCapability.GLOB, '.respec-ai/config/standards/*.toml')

    # sync_plan_instructions (Step 2.1) retrieves the plan from the platform before the
    # refinement loop starts, using the platform's own plan-retrieval tool -- not the
    # phase-scoped tools above. Undeclared otherwise (same defect class as finding F20).
    platform_plan_retrieval_tool = get_platform_adapter(platform_type).retrieve_plan_tool
    builder.add_platform_tools(
        [create_phase_tool, phase_retrieval_tool, phase_listing_tool, platform_plan_retrieval_tool]
    )

    return PhaseCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        create_phase_tool=create_phase_tool,
        platform=platform_type,
        plans_dir=plans_dir,
        invoke_phase_architect=adapter.render_agent_invocation(
            'respec-phase-architect',
            'design technical phase architecture',
            [
                ('loop_id', 'LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('phase_mode', 'detail'),
                ('optional_instructions', 'OPTIONAL_INSTRUCTIONS'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_phase_architect_shape=adapter.render_agent_invocation(
            'respec-phase-architect',
            'design phase shape: public seams, skeleton index, open design decisions',
            [
                ('loop_id', 'SHAPE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('phase_mode', 'shape'),
                ('optional_instructions', 'OPTIONAL_INSTRUCTIONS'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_phase_architect_implementation_plan=adapter.render_agent_invocation(
            'respec-phase-architect',
            'design implementation plan: build order, execution intent, deferred risks',
            [
                ('loop_id', 'SHAPE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('phase_mode', 'implementation-plan'),
                ('optional_instructions', 'OPTIONAL_INSTRUCTIONS'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_phase_critic=adapter.render_agent_invocation(
            'respec-phase-critic',
            'evaluate phase quality against FSDD framework',
            [
                ('plan_name', 'PLAN_NAME'),
                ('loop_id', 'LOOP_ID'),
                ('phase_name', 'PHASE_NAME'),
                ('phase_mode', 'detail'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        invoke_phase_critic_shape=adapter.render_agent_invocation(
            'respec-phase-critic',
            'evaluate approved phase shape as a safety net, not a gatekeeper',
            [
                ('plan_name', 'PLAN_NAME'),
                ('loop_id', 'SHAPE_LOOP_ID'),
                ('phase_name', 'PHASE_NAME'),
                ('phase_mode', 'shape'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        invoke_phase_critic_post_synthesis=adapter.render_agent_invocation(
            'respec-phase-critic',
            'run post-synthesis research-path and API coverage validation',
            [
                ('plan_name', 'PLAN_NAME'),
                ('loop_id', 'LOOP_ID'),
                ('phase_name', 'PHASE_NAME'),
                ('validation_mode', 'post_synthesis'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        phase_command_reference=adapter.render_command_reference('respec-phase'),
        roadmap_command_invocation=adapter.render_command_invocation(
            'respec-roadmap',
            '{PLAN_NAME}',
            '',
            requires_user_interaction=False,
        ),
        plan_command_invocation=adapter.render_command_invocation(
            'respec-plan',
            '[plan-name] [optional: initial context]',
            '',
            requires_user_interaction=False,
        ),
        code_command_invocation=adapter.render_command_invocation(
            'respec-code',
            '{PLAN_NAME} {PHASE_NAME} [optional: additional-context]',
            '',
            requires_user_interaction=False,
        ),
        store_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}', content='{STRATEGIC_PLAN_MARKDOWN}'
        ),
        store_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{EXTRACTED_PHASE_MARKDOWN}',
        ),
        initialize_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        link_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{LOOP_ID}',
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        link_shape_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{SHAPE_LOOP_ID}',
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='{LOOP_ID}'),
        get_shape_loop_status=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_LOOP_STATUS, loop_id='{SHAPE_LOOP_ID}'
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{LOOP_ID}'
        ),
        decide_shape_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{SHAPE_LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', loop_id='{LOOP_ID}'
        ),
        get_shape_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', loop_id='{SHAPE_LOOP_ID}'
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{USER_FEEDBACK_MARKDOWN}'
        ),
        store_shape_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{SHAPE_LOOP_ID}', feedback_markdown='{USER_FEEDBACK_MARKDOWN}'
        ),
        validate_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.VALIDATE_DOCUMENT, doc_type='"phase"', content='{CONTENT_TO_VALIDATE}'
        ),
        store_document_gate_edit=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{RECONCILED_PHASE_MARKDOWN}',
            allow_frozen_field_edits='true',
        ),
    )


def create_plan_command_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    plans_dir: str = '~/.claude/plans',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PlanCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_task_agent(RespecAIAgent.PLAN_CONVERSATION)
    builder.add_task_agent(RespecAIAgent.PLAN_CRITIC)
    builder.add_task_agent(RespecAIAgent.PLAN_ANALYST)
    builder.add_task_agent(RespecAIAgent.ANALYST_CRITIC)
    builder.add_builtin_tool(BuiltInToolCapability.READ)
    builder.add_builtin_tool(BuiltInToolCapability.WRITE, '.respec-ai/plans/*/references/*.md')
    builder.add_builtin_tool(BuiltInToolCapability.BASH)

    for tool in PlanCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    return PlanCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        create_project_external=platform_tools[0],
        get_plan_tool=platform_tools[1],
        platform=platform_type,
        plans_dir=plans_dir,
        invoke_plan_critic=adapter.render_agent_invocation(
            'respec-plan-critic',
            'evaluate strategic plan quality',
            [('plan_name', 'PLAN_NAME'), ('previous_feedback_markdown', 'PRIOR_CRITIC_FEEDBACK')],
        ),
        invoke_plan_analyst=adapter.render_agent_invocation(
            'respec-plan-analyst',
            'extract structured objectives from strategic plan',
            [('loop_id', 'ANALYST_LOOP_ID')],
        ),
        invoke_analyst_critic=adapter.render_agent_invocation(
            'respec-analyst-critic',
            'validate business objective extraction quality',
            [('loop_id', 'ANALYST_LOOP_ID')],
        ),
        conversation_invocation=adapter.render_command_invocation(
            'respec-plan-conversation',
            '[CONVERSATION_INITIAL_CONTEXT]',
            PLAN_CONVERSATION_INLINE_GUIDE,
            requires_user_interaction=True,
        ),
        conversation_workflow_name=adapter.conversation_workflow_name,
        roadmap_command_invocation=adapter.render_command_invocation(
            'respec-roadmap',
            '{PLAN_NAME}',
            '',
            requires_user_interaction=False,
        ),
        phase_command_invocation=adapter.render_command_invocation(
            'respec-phase',
            '{PLAN_NAME} [phase-name]',
            '',
            requires_user_interaction=False,
        ),
        initialize_plan_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"plan"'
        ),
        initialize_analyst_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"analyst"'
        ),
        store_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}', content='{CURRENT_PLAN}'
        ),
        store_plan_in_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"plan"',
            key='{ANALYST_LOOP_ID}',
            content='{PLAN_FROM_PREVIOUS_STEP}',
        ),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_LOOP_STATUS, loop_id='{ANALYST_LOOP_ID}'
        ),
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='{ANALYST_LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{ANALYST_LOOP_ID}', count='1'
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{ANALYST_LOOP_ID}'
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{PLAN_LOOP_ID}', feedback_markdown='{USER_FEEDBACK}'
        ),
    )


def create_code_command_tools(
    phase_retrieval_tool: str,
    phase_comment_tool: str,
    platform_type: 'PlatformType',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'CodeCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_task_agent(RespecAIAgent.CODER)
    builder.add_task_agent(RespecAIAgent.AUTOMATED_QUALITY_CHECKER)
    builder.add_task_agent(RespecAIAgent.SPEC_ALIGNMENT_REVIEWER)
    builder.add_task_agent(RespecAIAgent.DESIGN_CONFORMANCE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODE_QUALITY_REVIEWER)
    builder.add_task_agent(RespecAIAgent.FRONTEND_REVIEWER)
    builder.add_task_agent(RespecAIAgent.BACKEND_API_REVIEWER)
    builder.add_task_agent(RespecAIAgent.DATABASE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.INFRASTRUCTURE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODING_STANDARDS_REVIEWER)
    _add_adapter_question_tool(builder, adapter)
    builder.add_builtin_tool(BuiltInToolCapability.BASH)
    builder.add_bash_script('scripts/detect-packages.sh:*')

    for tool in CodeCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools([phase_retrieval_tool, phase_comment_tool])
    builder.add_builtin_tool(BuiltInToolCapability.READ, '.respec-ai/plans/*/phases/*/implementation.md')

    _reviewer_params = [
        ('coding_loop_id', 'CODING_LOOP_ID'),
        ('review_iteration', 'REVIEW_ITERATION'),
        ('phase_loop_id', 'PHASE_LOOP_ID'),
        ('plan_name', 'PLAN_NAME'),
        ('phase_name', 'PHASE_NAME'),
        ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
        ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
    ]
    return CodeCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        platform=platform_type,
        invoke_coder=adapter.render_agent_invocation(
            'respec-coder',
            'implement code following TDD methodology',
            [
                ('coding_loop_id', 'CODING_LOOP_ID'),
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', 'None'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        commit_command_invocation=adapter.render_command_invocation(
            'respec-commit',
            '{COMMIT_KIND}',
            'Use the respec-commit command with COMMIT_KIND from current context.',
        ),
        invoke_quality_checker=adapter.render_agent_invocation(
            'respec-automated-quality-checker',
            'run automated static analysis and quality checks',
            _reviewer_params,
        ),
        invoke_spec_alignment=adapter.render_agent_invocation(
            'respec-spec-alignment-reviewer',
            'verify implementation matches the implementation plan and Phase objectives',
            _reviewer_params,
        ),
        invoke_code_quality=adapter.render_agent_invocation(
            'respec-code-quality-reviewer',
            'assess code structural quality and design principles',
            _reviewer_params,
        ),
        invoke_dynamic_reviewer_pattern=adapter.render_agent_invocation(
            '{REVIEWER}',
            'perform domain-specific code review',
            _reviewer_params,
        ),
        phase1_review_parallel_policy=adapter.render_parallel_fanout_policy(
            'Phase 1 review agents',
            'structured reviewer results for all active reviewers',
        ),
        invoke_coder_standards=adapter.render_agent_invocation(
            'respec-coder',
            'apply coding standards fixes',
            [
                ('coding_loop_id', 'STANDARDS_LOOP_ID'),
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', '"standards-only"'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
                ('reviewer_feedback_context_markdown', 'REVIEWER_FEEDBACK_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_coding_standards_reviewer=adapter.render_agent_invocation(
            'respec-coding-standards-reviewer',
            'evaluate code against project coding standards',
            [
                ('coding_loop_id', 'STANDARDS_LOOP_ID'),
                ('review_iteration', 'REVIEW_ITERATION'),
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
                ('changed_files_scope_markdown', 'CHANGED_FILES_SCOPE_MARKDOWN'),
            ],
        ),
        phase_command_invocation=adapter.render_command_invocation(
            'respec-phase',
            '{PLAN_NAME} {PHASE_NAME} [optional: additional-context]',
            '',
            requires_user_interaction=False,
        ),
        code_command_invocation=adapter.render_command_invocation(
            'respec-code',
            '{PLAN_NAME} {PHASE_NAME} [optional: additional-context]',
            '',
            requires_user_interaction=False,
        ),
        store_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{PHASE_MARKDOWN}',
        ),
        get_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        initialize_coding_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        initialize_phase_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        initialize_standards_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        decide_coding_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{CODING_LOOP_ID}'
        ),
        decide_standards_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{STANDARDS_LOOP_ID}'
        ),
        consolidate_review_cycle=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.CONSOLIDATE_REVIEW_CYCLE,
            loop_id='{LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            active_reviewers='{ACTIVE_REVIEWERS}',
        ),
        get_standards_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{STANDARDS_LOOP_ID}', count='1'
        ),
        get_reviewer_feedback_context=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_REVIEWER_FEEDBACK_CONTEXT,
            loop_id='{STANDARDS_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            active_reviewers='["coding-standards-reviewer"]',
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{USER_FEEDBACK_MARKDOWN}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        link_phase_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{PHASE_LOOP_ID}',
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        get_design_conformance_write_back=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_REVIEW_SECTION, key='"{PLAN_NAME}/{PHASE_NAME}/design-conformance-write-back"'
        ),
    )


def create_roadmap_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PlanRoadmapCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_task_agent(RespecAIAgent.ROADMAP)
    builder.add_task_agent(RespecAIAgent.ROADMAP_CRITIC)
    builder.add_task_agent(RespecAIAgent.CREATE_PHASE)
    _add_adapter_question_tool(builder, adapter)

    for tool in PlanRoadmapCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanRoadmapCommandTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(platform_tools)

    return PlanRoadmapCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_plan_tool=platform_tools[0],
        list_project_phases_tool=platform_tools[1],
        platform=platform_type,
        invoke_roadmap_agent=adapter.render_agent_invocation(
            'respec-roadmap',
            'generate implementation roadmap from strategic plan',
            [
                ('loop_id', 'ROADMAP_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phasing_preferences', 'PHASING_PREFERENCES'),
            ],
        ),
        invoke_roadmap_critic=adapter.render_agent_invocation(
            'respec-roadmap-critic',
            'evaluate roadmap quality against FSDD framework',
            [('plan_name', 'PLAN_NAME'), ('loop_id', 'ROADMAP_LOOP_ID')],
        ),
        phase_extraction_parallel_policy=adapter.render_parallel_fanout_policy(
            'create-phase agents',
            'one completion result per roadmap phase',
        ),
        plan_command_invocation=adapter.render_command_invocation(
            'respec-plan',
            '[plan-name] [optional: initial context]',
            '',
            requires_user_interaction=False,
        ),
        phase_command_invocation=adapter.render_command_invocation(
            'respec-phase',
            '{PLAN_NAME} [phase-name]',
            '',
            requires_user_interaction=False,
        ),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        initialize_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"roadmap"'
        ),
        create_roadmap=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT, doc_type='"roadmap"', key='{PLAN_NAME}', content='{ROADMAP_MARKDOWN}'
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_LOOP_STATUS, loop_id='{ROADMAP_LOOP_ID}'
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{ROADMAP_LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{ROADMAP_LOOP_ID}', count='1'
        ),
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"roadmap"', key='{PLAN_NAME}'
        ),
    )


def create_plan_conversation_command_tools(
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PlanConversationCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    return PlanConversationCommandTools(tui_adapter=adapter)


def create_standards_command_tools(
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'StandardsCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_builtin_tool(BuiltInToolCapability.READ, '.respec-ai/config/*.toml')
    builder.add_builtin_tool(BuiltInToolCapability.READ, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInToolCapability.WRITE, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInToolCapability.EDIT, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInToolCapability.GLOB, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInToolCapability.READ, '.respec-ai/config/standards/guides/*.md')
    builder.add_builtin_tool(BuiltInToolCapability.WRITE, '.respec-ai/config/standards/guides/*.md')
    builder.add_builtin_tool(BuiltInToolCapability.EDIT, '.respec-ai/config/standards/guides/*.md')
    builder.add_builtin_tool(BuiltInToolCapability.GLOB, '.respec-ai/config/standards/guides/*.md')
    _add_adapter_question_tool(builder, adapter)
    return StandardsCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
    )


def create_design_sync_command_tools(
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'DesignSyncCommandTools':
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_builtin_tool(BuiltInToolCapability.DESIGN_SYNC)
    return DesignSyncCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
    )


def create_phase_architect_agent_tools(
    tui_adapter: TuiAdapter, plans_dir: str = '~/.claude/plans'
) -> PhaseArchitectAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in PhaseArchitectAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PhaseArchitectAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    # Optional (F32): grants DesignSync where the adapter supports it (Claude Code) and
    # silently skips it elsewhere (OpenCode, Codex) rather than raising (F17).
    builder.add_optional_builtin_tool(BuiltInToolCapability.DESIGN_SYNC)

    return PhaseArchitectAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        plans_dir=plans_dir,
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='{LOOP_ID}'),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='None', loop_id='{LOOP_ID}'
        ),
        update_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.UPDATE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{GENERATED_PHASE_MARKDOWN}',
        ),
    )


def create_phase_critic_agent_tools(
    tui_adapter: TuiAdapter, phase_length_soft_cap: int, phase_shape_soft_cap: int
) -> PhaseCriticAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in PhaseCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PhaseCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PhaseCriticAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        phase_length_soft_cap=phase_length_soft_cap,
        phase_shape_soft_cap=phase_shape_soft_cap,
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='None', loop_id='{LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='2'
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='{LOOP_ID}'),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{GENERATED_FEEDBACK}'
        ),
    )


def create_analyst_critic_agent_tools(tui_adapter: TuiAdapter) -> AnalystCriticAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in AnalystCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in AnalystCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return AnalystCriticAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{LOOP_ID}'
        ),
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='{LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='2'
        ),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{GENERATED_FEEDBACK}'
        ),
    )


def create_plan_analyst_agent_tools(tui_adapter: TuiAdapter) -> PlanAnalystAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in PlanAnalystAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanAnalystAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PlanAnalystAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{LOOP_ID}'
        ),
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='{LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        store_current_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CURRENT_ANALYSIS, loop_id='{LOOP_ID}', analysis='{ANALYSIS}'
        ),
    )


def create_plan_critic_agent_tools(tui_adapter: TuiAdapter) -> PlanCriticAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in PlanCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PlanCriticAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
    )


def create_roadmap_agent_tools(tui_adapter: TuiAdapter, plans_dir: str = '~/.claude/plans') -> RoadmapAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in RoadmapAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in RoadmapAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return RoadmapAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        plans_dir=plans_dir,
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='{LOOP_ID}'),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        create_roadmap=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.CREATE_ROADMAP, plan_name='{PLAN_NAME}', roadmap_data='{ROADMAP_MARKDOWN}'
        ),
    )


def create_roadmap_critic_agent_tools(tui_adapter: TuiAdapter) -> RoadmapCriticAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in RoadmapCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in RoadmapCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return RoadmapCriticAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='2'
        ),
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_ROADMAP, plan_name='{PLAN_NAME}'),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{GENERATED_FEEDBACK}'
        ),
    )


def create_coder_agent_tools(
    tui_adapter: TuiAdapter,
) -> CoderAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in CoderAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in CoderAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_builtin_tool(BuiltInToolCapability.READ, '.respec-ai/plans/*/phases/*/implementation.md')

    return CoderAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
    )


def create_create_phase_agent_tools(
    tui_adapter: TuiAdapter, platform_tools: list[str], platform: PlatformType
) -> CreatePhaseAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in CreatePhaseAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    return CreatePhaseAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        create_phase_tool=platform_tools[0],
        get_phase_tool=platform_tools[1],
        update_phase_tool=platform_tools[2],
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"roadmap"', key='{PLAN_NAME}'
        ),
        store_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{EXTRACTED_PHASE_MARKDOWN}',
        ),
        platform=platform,
    )


def create_commit_command_tools(tui_adapter: TuiAdapter) -> CommitCommandTools:
    builder = TemplateToolBuilder(tui_adapter)
    for builtin_tool, params in CommitCommandTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return CommitCommandTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
    )


def create_automated_quality_checker_agent_tools(tui_adapter: TuiAdapter) -> AutomatedQualityCheckerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in AutomatedQualityCheckerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in AutomatedQualityCheckerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return AutomatedQualityCheckerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"automated-quality-checker"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='50',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_design_conformance_reviewer_agent_tools(tui_adapter: TuiAdapter) -> DesignConformanceReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in DesignConformanceReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in DesignConformanceReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return DesignConformanceReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"design-conformance-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='50',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
        store_write_back=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEW_SECTION,
            key='"{PLAN_NAME}/{PHASE_NAME}/design-conformance-write-back"',
            content='{WRITE_BACK_MARKDOWN}',
        ),
    )


def create_spec_alignment_reviewer_agent_tools(tui_adapter: TuiAdapter) -> SpecAlignmentReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in SpecAlignmentReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in SpecAlignmentReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return SpecAlignmentReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"spec-alignment-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='50',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_code_quality_reviewer_agent_tools(tui_adapter: TuiAdapter) -> CodeQualityReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in CodeQualityReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in CodeQualityReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return CodeQualityReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"code-quality-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='25',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_frontend_reviewer_agent_tools(tui_adapter: TuiAdapter) -> FrontendReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in FrontendReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in FrontendReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(FrontendReviewerAgentTools.browser_tools)

    return FrontendReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"frontend-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='25',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_backend_api_reviewer_agent_tools(tui_adapter: TuiAdapter) -> BackendApiReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in BackendApiReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in BackendApiReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return BackendApiReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"backend-api-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='25',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_database_reviewer_agent_tools(tui_adapter: TuiAdapter) -> DatabaseReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in DatabaseReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in DatabaseReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return DatabaseReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"database-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='25',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_infrastructure_reviewer_agent_tools(tui_adapter: TuiAdapter) -> InfrastructureReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in InfrastructureReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in InfrastructureReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return InfrastructureReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"infrastructure-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='25',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_coding_standards_reviewer_agent_tools(tui_adapter: TuiAdapter) -> CodingStandardsReviewerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in CodingStandardsReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in CodingStandardsReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return CodingStandardsReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_implementation_plan='Read(.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md)',
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"coding-standards-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            max_score='25',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
    )


def create_patch_planner_agent_tools(tui_adapter: TuiAdapter) -> PatchPlannerAgentTools:
    builder = TemplateToolBuilder(tui_adapter)

    for tool in PatchPlannerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PatchPlannerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PatchPlannerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_amendment_scope=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_REVIEW_SECTION, key='{AMENDMENT_SCOPE_KEY}'
        ),
        store_amendment_scope=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEW_SECTION,
            key='{AMENDMENT_SCOPE_KEY}',
            content='{AMENDMENT_SCOPE_MARKDOWN}',
        ),
    )


def create_patch_command_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    plans_dir: str = '~/.claude/plans',
    tui_adapter: 'TuiAdapter | None' = None,
) -> PatchCommandTools:
    adapter = _resolve_tui_adapter(tui_adapter)
    builder = TemplateToolBuilder(adapter)
    builder.add_task_agent(RespecAIAgent.PATCH_PLANNER)
    builder.add_task_agent(RespecAIAgent.CODER)
    builder.add_task_agent(RespecAIAgent.AUTOMATED_QUALITY_CHECKER)
    builder.add_task_agent(RespecAIAgent.SPEC_ALIGNMENT_REVIEWER)
    builder.add_task_agent(RespecAIAgent.DESIGN_CONFORMANCE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODE_QUALITY_REVIEWER)
    builder.add_task_agent(RespecAIAgent.FRONTEND_REVIEWER)
    builder.add_task_agent(RespecAIAgent.BACKEND_API_REVIEWER)
    builder.add_task_agent(RespecAIAgent.DATABASE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.INFRASTRUCTURE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODING_STANDARDS_REVIEWER)
    _add_adapter_question_tool(builder, adapter)
    builder.add_builtin_tool(BuiltInToolCapability.BASH)
    builder.add_builtin_tool(BuiltInToolCapability.GLOB)
    builder.add_builtin_tool(BuiltInToolCapability.READ, '.respec-ai/plans/*/phases/*/phase.md')
    builder.add_bash_script('scripts/detect-packages.sh:*')

    for tool in PatchCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    _reviewer_params = [
        ('coding_loop_id', 'CODING_LOOP_ID'),
        ('review_iteration', 'REVIEW_ITERATION'),
        ('phase_loop_id', 'PHASE_LOOP_ID'),
        ('plan_name', 'PLAN_NAME'),
        ('phase_name', 'PHASE_NAME'),
        ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
        ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
    ]
    return PatchCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        platform=platform_type,
        plans_dir=plans_dir,
        invoke_patch_planner=adapter.render_agent_invocation(
            'respec-patch-planner',
            'scope amendment from clarified patch request',
            [
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('execution_mode', 'EXECUTION_MODE'),
                ('request_brief', 'PATCH_REQUEST_BRIEF'),
            ],
        ),
        invoke_coder=adapter.render_agent_invocation(
            'respec-coder',
            'implement code changes following TDD methodology',
            [
                ('coding_loop_id', 'CODING_LOOP_ID'),
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', 'None'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        commit_command_invocation=adapter.render_command_invocation(
            'respec-commit',
            '{COMMIT_KIND}',
            'Use the respec-commit command with COMMIT_KIND from current context.',
        ),
        invoke_quality_checker=adapter.render_agent_invocation(
            'respec-automated-quality-checker',
            'run automated static analysis and quality checks',
            _reviewer_params,
        ),
        invoke_spec_alignment=adapter.render_agent_invocation(
            'respec-spec-alignment-reviewer',
            'verify implementation matches the implementation plan and Phase objectives',
            _reviewer_params,
        ),
        invoke_code_quality=adapter.render_agent_invocation(
            'respec-code-quality-reviewer',
            'assess code structural quality and design principles',
            _reviewer_params,
        ),
        invoke_dynamic_reviewer_pattern=adapter.render_agent_invocation(
            '{REVIEWER}',
            'perform domain-specific code review',
            _reviewer_params,
        ),
        phase1_review_parallel_policy=adapter.render_parallel_fanout_policy(
            'Phase 1 review agents',
            'structured reviewer results for all active reviewers',
        ),
        invoke_coder_standards=adapter.render_agent_invocation(
            'respec-coder',
            'apply coding standards fixes',
            [
                ('coding_loop_id', 'STANDARDS_LOOP_ID'),
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', '"standards-only"'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
                ('reviewer_feedback_context_markdown', 'REVIEWER_FEEDBACK_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_coding_standards_reviewer=adapter.render_agent_invocation(
            'respec-coding-standards-reviewer',
            'evaluate code against project coding standards',
            [
                ('coding_loop_id', 'STANDARDS_LOOP_ID'),
                ('review_iteration', 'REVIEW_ITERATION'),
                ('phase_loop_id', 'PHASE_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
                ('changed_files_scope_markdown', 'CHANGED_FILES_SCOPE_MARKDOWN'),
            ],
        ),
        roadmap_command_invocation=adapter.render_command_invocation(
            'respec-roadmap',
            '{PLAN_NAME}',
            '',
            requires_user_interaction=False,
        ),
        phase_command_invocation=adapter.render_command_invocation(
            'respec-phase',
            '{PLAN_NAME} {PHASE_NAME} [optional: additional-context]',
            '',
            requires_user_interaction=False,
        ),
        store_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{PHASE_MARKDOWN}',
        ),
        get_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        update_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.UPDATE_DOCUMENT,
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{UPDATED_PHASE_MARKDOWN}',
        ),
        initialize_phase_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        link_phase_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{PHASE_LOOP_ID}',
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        initialize_coding_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        decide_coding_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{CODING_LOOP_ID}'
        ),
        consolidate_review_cycle=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.CONSOLIDATE_REVIEW_CYCLE,
            loop_id='{LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            active_reviewers='{ACTIVE_REVIEWERS}',
        ),
        initialize_standards_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"phase"'
        ),
        decide_standards_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{STANDARDS_LOOP_ID}'
        ),
        get_standards_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{STANDARDS_LOOP_ID}', count='1'
        ),
        get_reviewer_feedback_context=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_REVIEWER_FEEDBACK_CONTEXT,
            loop_id='{STANDARDS_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            active_reviewers='["coding-standards-reviewer"]',
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='{LOOP_ID}'),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{USER_FEEDBACK_MARKDOWN}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        get_amendment_scope=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_REVIEW_SECTION, key='{AMENDMENT_SCOPE_KEY}'
        ),
        get_design_conformance_write_back=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_REVIEW_SECTION, key='"{PLAN_NAME}/{PHASE_NAME}/design-conformance-write-back"'
        ),
    )
