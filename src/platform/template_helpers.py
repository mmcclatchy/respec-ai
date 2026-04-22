from src.models.enums import DocumentType

from .tui_adapters.claude_code import ClaudeCodeAdapter as _ClaudeCodeAdapter
from .models import (
    AnalystCriticAgentTools,
    AutomatedQualityCheckerAgentTools,
    BackendApiReviewerAgentTools,
    CodeCommandTools,
    CoderAgentTools,
    CodeQualityReviewerAgentTools,
    CodingStandardsReviewerAgentTools,
    CreatePhaseAgentTools,
    DatabaseReviewerAgentTools,
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
    TaskCommandTools,
    TaskPlanCriticAgentTools,
    TaskPlannerAgentTools,
    ToolReference,
)
from .platform_selector import PlatformType
from .tool_doc_generator import ToolDocGenerator
from .tool_enums import BuiltInTool, RespecAIAgent, RespecAITool
from .tui_adapters.base import TuiAdapter


class TemplateToolBuilder:
    def __init__(self) -> None:
        self.tools: list[ToolReference] = []

    def add_task_agent(self, agent_name: RespecAIAgent) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInTool.TASK, parameters=agent_name))
        return self

    def add_bash_script(self, script_path: str) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInTool.BASH, parameters=script_path))
        return self

    def add_respec_ai_tool(self, tool: RespecAITool) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=tool))
        return self

    def add_builtin_tool(self, tool: BuiltInTool, parameters: str = '') -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=tool, parameters=parameters))
        return self

    def add_platform_tools(self, platform_tools: list[str]) -> 'TemplateToolBuilder':
        for tool_string in platform_tools:
            # For platform tools, we don't validate the enum since they're already processed
            # Just store them as plain strings in the final tools list
            self.tools.append(ToolReference(tool=BuiltInTool.TASK, parameters=f'__PLATFORM_TOOL__{tool_string}'))
        return self

    def build(self) -> list[str]:
        tool_strings = []
        for tool_ref in self.tools:
            rendered = tool_ref.render()
            # Handle special platform tool case
            if rendered.startswith('Task(__PLATFORM_TOOL__') and rendered.endswith(')'):
                # Extract the actual tool string
                tool_string = rendered[len('Task(__PLATFORM_TOOL__') : -1]
                tool_strings.append(tool_string)
            else:
                tool_strings.append(rendered)
        return tool_strings

    def render_yaml_tools(self, indent: str = '  ') -> str:
        tool_strings = self.build()
        return '\n'.join(f'{indent}- {tool}' for tool in tool_strings)

    def render_comma_separated_tools(self) -> str:
        tool_strings = self.build()
        return ', '.join(tool_strings)


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
    platform_tools: list[str],
    platform_type: 'PlatformType',
    plans_dir: str = '~/.claude/plans',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PhaseCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
    builder.add_task_agent(RespecAIAgent.PHASE_CRITIC)
    builder.add_builtin_tool(BuiltInTool.TASK, 'bp')
    builder.add_builtin_tool(BuiltInTool.BASH, '')

    for tool in PhaseCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    adapter = _resolve_tui_adapter(tui_adapter)
    return PhaseCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        create_phase_tool=platform_tools[0],
        get_phase_tool=platform_tools[1],
        update_phase_tool=platform_tools[2],
        platform=platform_type,
        plans_dir=plans_dir,
        invoke_phase_architect=adapter.render_agent_invocation(
            'respec-phase-architect',
            'design technical phase architecture',
            [
                ('loop_id', 'LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('optional_instructions', 'OPTIONAL_INSTRUCTIONS'),
            ],
        ),
        invoke_phase_critic=adapter.render_agent_invocation(
            'respec-phase-critic',
            'evaluate phase quality against FSDD framework',
            [('plan_name', 'PLAN_NAME'), ('loop_id', 'LOOP_ID'), ('phase_name', 'PHASE_NAME')],
        ),
        task_command_invocation=adapter.render_command_invocation(
            'respec-task',
            '{PLAN_NAME} {PHASE_NAME} [optional: additional-context]',
            '',
            requires_user_interaction=False,
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
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='{LOOP_ID}'),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', loop_id='{LOOP_ID}'
        ),
    )


def create_plan_command_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    plans_dir: str = '~/.claude/plans',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PlanCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.PLAN_CONVERSATION)
    builder.add_task_agent(RespecAIAgent.PLAN_CRITIC)
    builder.add_task_agent(RespecAIAgent.PLAN_ANALYST)
    builder.add_task_agent(RespecAIAgent.ANALYST_CRITIC)
    builder.add_builtin_tool(BuiltInTool.READ)
    builder.add_builtin_tool(BuiltInTool.WRITE, '.respec-ai/plans/*/references/*.md')
    builder.add_builtin_tool(BuiltInTool.BASH)

    for tool in PlanCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    adapter = _resolve_tui_adapter(tui_adapter)
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
            [('plan_name', 'PLAN_NAME')],
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
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='{ANALYST_LOOP_ID}'
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{ANALYST_LOOP_ID}'
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{PLAN_LOOP_ID}', feedback_markdown='{USER_FEEDBACK}'
        ),
    )


def create_code_command_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'CodeCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.CODER)
    builder.add_task_agent(RespecAIAgent.AUTOMATED_QUALITY_CHECKER)
    builder.add_task_agent(RespecAIAgent.SPEC_ALIGNMENT_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODE_QUALITY_REVIEWER)
    builder.add_task_agent(RespecAIAgent.FRONTEND_REVIEWER)
    builder.add_task_agent(RespecAIAgent.BACKEND_API_REVIEWER)
    builder.add_task_agent(RespecAIAgent.DATABASE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.INFRASTRUCTURE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODING_STANDARDS_REVIEWER)
    builder.add_builtin_tool(BuiltInTool.ASK_USER_QUESTION)
    builder.add_builtin_tool(BuiltInTool.BASH)
    builder.add_bash_script('scripts/detect-packages.sh:*')

    for tool in CodeCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    adapter = _resolve_tui_adapter(tui_adapter)
    _reviewer_params = [
        ('coding_loop_id', 'CODING_LOOP_ID'),
        ('review_iteration', 'REVIEW_ITERATION'),
        ('task_loop_id', 'TASK_LOOP_ID'),
        ('plan_name', 'PLAN_NAME'),
        ('phase_name', 'PHASE_NAME'),
        ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
    ]
    return CodeCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_phase_tool=platform_tools[0],
        comment_phase_tool=platform_tools[1],
        platform=platform_type,
        invoke_coder=adapter.render_agent_invocation(
            'respec-coder',
            'implement code following TDD methodology',
            [
                ('coding_loop_id', 'CODING_LOOP_ID'),
                ('task_loop_id', 'TASK_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', 'None'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_quality_checker=adapter.render_agent_invocation(
            'respec-automated-quality-checker',
            'run automated static analysis and quality checks',
            _reviewer_params,
        ),
        invoke_spec_alignment=adapter.render_agent_invocation(
            'respec-spec-alignment-reviewer',
            'verify implementation matches Task and Phase objectives',
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
                ('task_loop_id', 'TASK_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', '"standards-only"'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_coding_standards_reviewer=adapter.render_agent_invocation(
            'respec-coding-standards-reviewer',
            'evaluate code against project coding standards',
            [
                ('coding_loop_id', 'STANDARDS_LOOP_ID'),
                ('review_iteration', 'REVIEW_ITERATION'),
                ('task_loop_id', 'TASK_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        task_command_invocation=adapter.render_command_invocation(
            'respec-task',
            '{PLAN_NAME} {PHASE_NAME} [optional: additional-context]',
            '',
            requires_user_interaction=False,
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
        store_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"task"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{BUILD_PLAN_MARKDOWN}',
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
        initialize_planning_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
        ),
        initialize_coding_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
        ),
        initialize_standards_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
        ),
        decide_planning_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{PLANNING_LOOP_ID}'
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
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{USER_FEEDBACK_MARKDOWN}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        get_task_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
    )


def create_roadmap_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'PlanRoadmapCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.ROADMAP)
    builder.add_task_agent(RespecAIAgent.ROADMAP_CRITIC)
    builder.add_task_agent(RespecAIAgent.CREATE_PHASE)

    for tool in PlanRoadmapCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanRoadmapCommandTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(platform_tools)

    adapter = _resolve_tui_adapter(tui_adapter)
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


def create_task_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    tui_adapter: 'TuiAdapter | None' = None,
) -> 'TaskCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.TASK_PLANNER)
    builder.add_task_agent(RespecAIAgent.TASK_PLAN_CRITIC)

    for tool in TaskCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in TaskCommandTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(platform_tools)

    adapter = _resolve_tui_adapter(tui_adapter)
    return TaskCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        get_phase_tool=platform_tools[0],
        list_phase_tasks_tool=platform_tools[1],
        platform=platform_type,
        invoke_task_planner=adapter.render_agent_invocation(
            'respec-task-planner',
            'generate Task document from Phase specification',
            [
                ('task_loop_id', 'TASK_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('reference_context_markdown', 'REFERENCE_CONTEXT_MARKDOWN'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        invoke_task_plan_critic=adapter.render_agent_invocation(
            'respec-task-plan-critic',
            'evaluate Task quality against FSDD criteria',
            [
                ('task_loop_id', 'TASK_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        task_command_reference=adapter.render_command_reference('respec-task'),
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
        initialize_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
        ),
        link_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{TASK_LOOP_ID}',
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{TASK_LOOP_ID}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{TASK_LOOP_ID}', count='1'
        ),
        get_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{TASK_LOOP_ID}'
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{TASK_LOOP_ID}', feedback_markdown='{USER_FEEDBACK}'
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
    builder = TemplateToolBuilder()
    adapter = _resolve_tui_adapter(tui_adapter)
    builder.add_builtin_tool(BuiltInTool.READ, '.respec-ai/config/*.toml')
    builder.add_builtin_tool(BuiltInTool.READ, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInTool.WRITE, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInTool.EDIT, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInTool.GLOB, '.respec-ai/config/standards/*.toml')
    builder.add_builtin_tool(BuiltInTool.READ, '.respec-ai/config/standards/guides/*.md')
    builder.add_builtin_tool(BuiltInTool.WRITE, '.respec-ai/config/standards/guides/*.md')
    builder.add_builtin_tool(BuiltInTool.EDIT, '.respec-ai/config/standards/guides/*.md')
    builder.add_builtin_tool(BuiltInTool.GLOB, '.respec-ai/config/standards/guides/*.md')
    if adapter.ask_user_question_tool_name:
        builder.add_builtin_tool(BuiltInTool.ASK_USER_QUESTION)
    return StandardsCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
    )


def create_phase_architect_agent_tools(
    tui_adapter: TuiAdapter, plans_dir: str = '~/.claude/plans'
) -> PhaseArchitectAgentTools:
    builder = TemplateToolBuilder()

    for tool in PhaseArchitectAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PhaseArchitectAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

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


def create_phase_critic_agent_tools(tui_adapter: TuiAdapter, phase_length_soft_cap: int) -> PhaseCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in PhaseCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PhaseCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PhaseCriticAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        phase_length_soft_cap=phase_length_soft_cap,
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"plan"', key='{PLAN_NAME}'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='None', loop_id='{LOOP_ID}'
        ),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{GENERATED_FEEDBACK}'
        ),
    )


def create_analyst_critic_agent_tools(tui_adapter: TuiAdapter) -> AnalystCriticAgentTools:
    builder = TemplateToolBuilder()

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
        store_current_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CURRENT_ANALYSIS, loop_id='{LOOP_ID}', analysis='{ANALYSIS}'
        ),
    )


def create_plan_analyst_agent_tools(tui_adapter: TuiAdapter) -> PlanAnalystAgentTools:
    builder = TemplateToolBuilder()

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
        store_current_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CURRENT_ANALYSIS, loop_id='{LOOP_ID}', analysis='{ANALYSIS}'
        ),
    )


def create_plan_critic_agent_tools(tui_adapter: TuiAdapter) -> PlanCriticAgentTools:
    builder = TemplateToolBuilder()

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
    builder = TemplateToolBuilder()

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
    builder = TemplateToolBuilder()

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
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_ROADMAP, plan_name='{PLAN_NAME}'),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{GENERATED_FEEDBACK}'
        ),
    )


def create_task_planner_agent_tools(tui_adapter: TuiAdapter) -> TaskPlannerAgentTools:
    builder = TemplateToolBuilder()

    for tool in TaskPlannerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in TaskPlannerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return TaskPlannerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{TASK_LOOP_ID}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{TASK_LOOP_ID}', count='1'
        ),
        store_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type=DocumentType.TASK.quoted,
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{TASK_MARKDOWN}',
        ),
        link_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{TASK_LOOP_ID}',
            doc_type='"task"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_LOOP_STATUS, loop_id='{TASK_LOOP_ID}'
        ),
    )


def create_task_plan_critic_agent_tools(tui_adapter: TuiAdapter) -> TaskPlanCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in TaskPlanCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in TaskPlanCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return TaskPlanCriticAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{TASK_LOOP_ID}'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{TASK_LOOP_ID}', count='2'
        ),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='{TASK_LOOP_ID}', feedback_markdown='{FEEDBACK_MARKDOWN}'
        ),
    )


def create_coder_agent_tools(
    tui_adapter: TuiAdapter,
    platform_tools: list[str],
) -> CoderAgentTools:
    builder = TemplateToolBuilder()

    for tool in CoderAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in CoderAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(platform_tools)

    return CoderAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        update_task_status=platform_tools[0],
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
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
    builder = TemplateToolBuilder()

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


def create_automated_quality_checker_agent_tools(tui_adapter: TuiAdapter) -> AutomatedQualityCheckerAgentTools:
    builder = TemplateToolBuilder()

    for tool in AutomatedQualityCheckerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in AutomatedQualityCheckerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return AutomatedQualityCheckerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
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
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_spec_alignment_reviewer_agent_tools(tui_adapter: TuiAdapter) -> SpecAlignmentReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in SpecAlignmentReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in SpecAlignmentReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return SpecAlignmentReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
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
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_code_quality_reviewer_agent_tools(tui_adapter: TuiAdapter) -> CodeQualityReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in CodeQualityReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in CodeQualityReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return CodeQualityReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
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
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_frontend_reviewer_agent_tools(tui_adapter: TuiAdapter) -> FrontendReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in FrontendReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in FrontendReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return FrontendReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"frontend-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_backend_api_reviewer_agent_tools(tui_adapter: TuiAdapter) -> BackendApiReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in BackendApiReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in BackendApiReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return BackendApiReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"backend-api-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_database_reviewer_agent_tools(tui_adapter: TuiAdapter) -> DatabaseReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in DatabaseReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in DatabaseReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return DatabaseReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"database-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_infrastructure_reviewer_agent_tools(tui_adapter: TuiAdapter) -> InfrastructureReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in InfrastructureReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in InfrastructureReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return InfrastructureReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', key='{PLAN_NAME}/{PHASE_NAME}'
        ),
        store_reviewer_result=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_REVIEWER_RESULT,
            loop_id='{CODING_LOOP_ID}',
            review_iteration='{REVIEW_ITERATION}',
            reviewer_name='"infrastructure-reviewer"',
            feedback_markdown='{REVIEW_SECTION_MARKDOWN}',
            score='{REVIEW_SCORE}',
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
    )


def create_coding_standards_reviewer_agent_tools(tui_adapter: TuiAdapter) -> CodingStandardsReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in CodingStandardsReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in CodingStandardsReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return CodingStandardsReviewerAgentTools(
        tui_adapter=tui_adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
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
            blockers='{BLOCKERS}',
            findings='{FINDINGS}',
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{CODING_LOOP_ID}'
        ),
    )


def create_patch_planner_agent_tools(tui_adapter: TuiAdapter) -> PatchPlannerAgentTools:
    builder = TemplateToolBuilder()

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
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{TASK_LOOP_ID}'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{TASK_LOOP_ID}', count='1'
        ),
        store_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type=DocumentType.TASK.quoted,
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{TASK_MARKDOWN}',
        ),
        link_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{TASK_LOOP_ID}',
            doc_type='"task"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_LOOP_STATUS, loop_id='{TASK_LOOP_ID}'
        ),
    )


def create_patch_command_tools(
    platform_tools: list[str],
    platform_type: 'PlatformType',
    plans_dir: str = '~/.claude/plans',
    tui_adapter: 'TuiAdapter | None' = None,
) -> PatchCommandTools:
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.PATCH_PLANNER)
    builder.add_task_agent(RespecAIAgent.TASK_PLAN_CRITIC)
    builder.add_task_agent(RespecAIAgent.CODER)
    builder.add_task_agent(RespecAIAgent.AUTOMATED_QUALITY_CHECKER)
    builder.add_task_agent(RespecAIAgent.SPEC_ALIGNMENT_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODE_QUALITY_REVIEWER)
    builder.add_task_agent(RespecAIAgent.FRONTEND_REVIEWER)
    builder.add_task_agent(RespecAIAgent.BACKEND_API_REVIEWER)
    builder.add_task_agent(RespecAIAgent.DATABASE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.INFRASTRUCTURE_REVIEWER)
    builder.add_task_agent(RespecAIAgent.CODING_STANDARDS_REVIEWER)
    builder.add_builtin_tool(BuiltInTool.ASK_USER_QUESTION)
    builder.add_builtin_tool(BuiltInTool.BASH)
    builder.add_builtin_tool(BuiltInTool.GLOB)
    builder.add_builtin_tool(BuiltInTool.READ, '.respec-ai/plans/*/phases/*.md')
    builder.add_builtin_tool(BuiltInTool.WRITE, '.respec-ai/plans/*/phases/*/tasks/*.md')
    builder.add_bash_script('scripts/detect-packages.sh:*')

    for tool in PatchCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    adapter = _resolve_tui_adapter(tui_adapter)
    _reviewer_params = [
        ('coding_loop_id', 'CODING_LOOP_ID'),
        ('review_iteration', 'REVIEW_ITERATION'),
        ('task_loop_id', 'PLANNING_LOOP_ID'),
        ('plan_name', 'PLAN_NAME'),
        ('phase_name', 'PHASE_NAME'),
        ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
    ]
    return PatchCommandTools(
        tui_adapter=adapter,
        tools_yaml=builder.render_comma_separated_tools(),
        platform=platform_type,
        plans_dir=plans_dir,
        invoke_patch_planner=adapter.render_agent_invocation(
            'respec-patch-planner',
            'generate amendment task document',
            [
                ('task_loop_id', 'PLANNING_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('execution_mode', 'EXECUTION_MODE'),
                ('request_brief', 'PATCH_REQUEST_BRIEF'),
            ],
        ),
        invoke_task_plan_critic=adapter.render_agent_invocation(
            'respec-task-plan-critic',
            'evaluate amendment task quality against FSDD criteria',
            [
                ('task_loop_id', 'PLANNING_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
            ],
        ),
        invoke_coder=adapter.render_agent_invocation(
            'respec-coder',
            'implement code changes following TDD methodology',
            [
                ('coding_loop_id', 'CODING_LOOP_ID'),
                ('task_loop_id', 'PLANNING_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', 'None'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_quality_checker=adapter.render_agent_invocation(
            'respec-automated-quality-checker',
            'run automated static analysis and quality checks',
            _reviewer_params,
        ),
        invoke_spec_alignment=adapter.render_agent_invocation(
            'respec-spec-alignment-reviewer',
            'verify implementation matches Task and Phase objectives',
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
                ('task_loop_id', 'PLANNING_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('mode', '"standards-only"'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
                ('project_config_context_markdown', 'PROJECT_CONFIG_CONTEXT_MARKDOWN'),
            ],
        ),
        invoke_coding_standards_reviewer=adapter.render_agent_invocation(
            'respec-coding-standards-reviewer',
            'evaluate code against project coding standards',
            [
                ('coding_loop_id', 'STANDARDS_LOOP_ID'),
                ('review_iteration', 'REVIEW_ITERATION'),
                ('task_loop_id', 'PLANNING_LOOP_ID'),
                ('plan_name', 'PLAN_NAME'),
                ('phase_name', 'PHASE_NAME'),
                ('workflow_guidance_markdown', 'WORKFLOW_GUIDANCE_MARKDOWN'),
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
        initialize_planning_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
        ),
        link_planning_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='{PLANNING_LOOP_ID}',
            doc_type='"phase"',
            key='{PLAN_NAME}/{PHASE_NAME}',
        ),
        decide_planning_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{PLANNING_LOOP_ID}'
        ),
        initialize_coding_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
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
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, plan_name='{PLAN_NAME}', loop_type='"task"'
        ),
        decide_standards_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='{STANDARDS_LOOP_ID}'
        ),
        get_standards_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{STANDARDS_LOOP_ID}', count='1'
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='{LOOP_ID}', feedback_markdown='{USER_FEEDBACK_MARKDOWN}'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='{LOOP_ID}', count='1'
        ),
        get_task_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='{PLANNING_LOOP_ID}'
        ),
        store_task_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"task"',
            key='{PLAN_NAME}/{PHASE_NAME}',
            content='{TASK_MARKDOWN}',
        ),
    )
