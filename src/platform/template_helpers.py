from .models import (
    AnalystCriticAgentTools,
    CodeCommandTools,
    CreatePhaseAgentTools,
    PhaseArchitectAgentTools,
    PhaseCommandTools,
    PhaseCriticAgentTools,
    PlanAnalystAgentTools,
    PlanCommandTools,
    PlanCriticAgentTools,
    PlanRoadmapCommandTools,
    RoadmapAgentTools,
    RoadmapCriticAgentTools,
    TaskCoderAgentTools,
    TaskCriticAgentTools,
    TaskReviewerAgentTools,
    ToolReference,
)
from .platform_selector import PlatformType
from .tool_doc_generator import ToolDocGenerator
from .tool_enums import BuiltInTool, RespecAIAgent, RespecAITool


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


def create_phase_command_tools(platform_tools: list[str], platform_type: 'PlatformType') -> 'PhaseCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.PHASE_ARCHITECT)
    builder.add_task_agent(RespecAIAgent.PHASE_CRITIC)
    builder.add_bash_script('~/.claude/scripts/research-advisor-archive-scan.sh:*')

    for tool in PhaseCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    return PhaseCommandTools(
        tools_yaml=builder.render_comma_separated_tools(),
        create_phase_tool=platform_tools[0],
        get_phase_tool=platform_tools[1],
        update_phase_tool=platform_tools[2],
        platform=platform_type,
        store_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_PROJECT_PLAN, project_name='PLAN_NAME', project_plan_markdown='strategic_plan_markdown'
        ),
        store_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            path='f"{PLAN_NAME}/{EXPECTED_PHASE_NAME}"',
            content='extracted_phase_markdown',
        ),
        initialize_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, project_name='PLAN_NAME', loop_type='"phase"'
        ),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, project_name='PLAN_NAME'
        ),
        link_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.LINK_LOOP_TO_DOCUMENT,
            loop_id='LOOP_ID',
            doc_type='"phase"',
            path='f"{PLAN_NAME}/{EXPECTED_PHASE_NAME}"',
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='LOOP_ID'),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='LOOP_ID'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='LOOP_ID', count='1'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', loop_id='LOOP_ID'
        ),
    )


def create_plan_command_tools(platform_tools: list[str], platform_type: 'PlatformType') -> 'PlanCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.PLAN_CONVERSATION)
    builder.add_task_agent(RespecAIAgent.PLAN_CRITIC)
    builder.add_task_agent(RespecAIAgent.PLAN_ANALYST)
    builder.add_task_agent(RespecAIAgent.ANALYST_CRITIC)

    for tool in PlanCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    return PlanCommandTools(
        tools_yaml=builder.render_comma_separated_tools(),
        create_project_external=platform_tools[0],
        create_project_completion_external=platform_tools[1],
        get_project_plan_tool=platform_tools[2],
        platform=platform_type,
        initialize_analyst_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, project_name='PROJECT_NAME', loop_type="'analyst'"
        ),
        store_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_PROJECT_PLAN, project_name='PROJECT_NAME', project_plan_markdown='CURRENT_PLAN'
        ),
        store_plan_in_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_PROJECT_PLAN,
            project_name='ANALYST_LOOP_ID',
            project_plan_markdown='plan_from_previous_step',
        ),
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, project_name='PROJECT_NAME'
        ),
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='ANALYST_LOOP_ID'
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='ANALYST_LOOP_ID'
        ),
        store_completion_report=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_PLAN_COMPLETION_REPORT,
            project_path='PROJECT_PATH',
            loop_id='ANALYST_LOOP_ID',
            completion_report_markdown='completion_report_markdown',
        ),
    )


def create_code_command_tools(platform_tools: list[str], platform_type: 'PlatformType') -> 'CodeCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.PHASE_PLANNER)
    builder.add_task_agent(RespecAIAgent.TASK_CRITIC)
    builder.add_task_agent(RespecAIAgent.TASK_CODER)
    builder.add_task_agent(RespecAIAgent.TASK_REVIEWER)
    builder.add_task_agent(RespecAIAgent.RESEARCH_SYNTHESIZER)
    builder.add_bash_script('~/.claude/scripts/detect-packages.sh:*')

    for tool in CodeCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    return CodeCommandTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_phase_tool=platform_tools[0],
        comment_phase_tool=platform_tools[1],
        platform=platform_type,
        store_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"task"',
            path='f"{PROJECT_NAME}/{PHASE_NAME}"',
            content='build_plan_markdown',
        ),
        store_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            path='f"{PROJECT_NAME}/{PHASE_NAME}"',
            content='PHASE_MARKDOWN',
        ),
        get_phase_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', path='f"{PROJECT_NAME}/{PHASE_NAME}"'
        ),
        initialize_planning_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, project_name='PROJECT_NAME', loop_type='"task"'
        ),
        initialize_coding_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, project_name='PROJECT_NAME', loop_type='"task"'
        ),
        decide_planning_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='PLANNING_LOOP_ID'
        ),
        decide_coding_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='CODING_LOOP_ID'
        ),
        store_user_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_USER_FEEDBACK, loop_id='LOOP_ID', feedback_markdown='USER_FEEDBACK_MARKDOWN'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='LOOP_ID', count='1'
        ),
        get_task_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='PLANNING_LOOP_ID'
        ),
    )


def create_roadmap_tools(platform_tools: list[str], platform_type: 'PlatformType') -> 'PlanRoadmapCommandTools':
    builder = TemplateToolBuilder()
    builder.add_task_agent(RespecAIAgent.ROADMAP)
    builder.add_task_agent(RespecAIAgent.ROADMAP_CRITIC)
    builder.add_task_agent(RespecAIAgent.CREATE_PHASE)

    for tool in PlanRoadmapCommandTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanRoadmapCommandTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(platform_tools)

    return PlanRoadmapCommandTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_project_plan_tool=platform_tools[0],
        list_project_phases_tool=platform_tools[1],
        platform=platform_type,
        get_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, project_name='PROJECT_NAME'
        ),
        initialize_loop=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.INITIALIZE_REFINEMENT_LOOP, project_name='PROJECT_NAME', loop_type='"roadmap"'
        ),
        create_roadmap=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.CREATE_ROADMAP, project_name='PROJECT_NAME', roadmap_data='roadmap_markdown'
        ),
        decide_loop_action=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.DECIDE_LOOP_NEXT_ACTION, loop_id='ROADMAP_LOOP_ID'
        ),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='ROADMAP_LOOP_ID', count='1'
        ),
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_ROADMAP, project_name='PROJECT_NAME'),
    )


def create_phase_architect_agent_tools() -> PhaseArchitectAgentTools:
    builder = TemplateToolBuilder()

    for tool in PhaseArchitectAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PhaseArchitectAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PhaseArchitectAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='loop_id'),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='loop_id', count='1'
        ),
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', path='None', loop_id='loop_id'
        ),
        update_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.UPDATE_DOCUMENT,
            doc_type='"phase"',
            path='f"{project_name}/{phase_name}"',
            content='generated_phaseification',
        ),
    )


def create_phase_critic_agent_tools(phase_length_soft_cap: int) -> PhaseCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in PhaseCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PhaseCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PhaseCriticAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        phase_length_soft_cap=phase_length_soft_cap,
        get_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', path='None', loop_id='loop_id'
        ),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='loop_id', feedback_markdown='generated_feedback'
        ),
    )


def create_analyst_critic_agent_tools() -> AnalystCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in AnalystCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in AnalystCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return AnalystCriticAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_project_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, loop_id='loop_id'
        ),
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='loop_id'
        ),
        store_current_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CURRENT_ANALYSIS, loop_id='loop_id', analysis='analysis'
        ),
    )


def create_plan_analyst_agent_tools() -> PlanAnalystAgentTools:
    builder = TemplateToolBuilder()

    for tool in PlanAnalystAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanAnalystAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PlanAnalystAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_project_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, loop_id='loop_id'
        ),
        get_previous_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PREVIOUS_ANALYSIS, loop_id='loop_id'
        ),
        store_current_analysis=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CURRENT_ANALYSIS, loop_id='loop_id', analysis='analysis'
        ),
    )


def create_plan_critic_agent_tools() -> PlanCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in PlanCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in PlanCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return PlanCriticAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_project_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, project_name='project_name'
        ),
    )


def create_roadmap_agent_tools() -> RoadmapAgentTools:
    builder = TemplateToolBuilder()

    for tool in RoadmapAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in RoadmapAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return RoadmapAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_project_plan=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_PROJECT_PLAN_MARKDOWN, project_name='PROJECT_NAME'
        ),
        get_loop_status=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_LOOP_STATUS, loop_id='loop_id'),
        get_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='loop_id', count='1'
        ),
        create_roadmap=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.CREATE_ROADMAP, project_name='PROJECT_NAME', roadmap_data='roadmap_markdown'
        ),
    )


def create_roadmap_critic_agent_tools() -> RoadmapCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in RoadmapCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in RoadmapCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return RoadmapCriticAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_ROADMAP, project_name='PROJECT_NAME'),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='LOOP_ID', feedback_markdown='generated_feedback'
        ),
    )


def create_task_critic_agent_tools() -> TaskCriticAgentTools:
    builder = TemplateToolBuilder()

    for tool in TaskCriticAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in TaskCriticAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return TaskCriticAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='planning_loop_id'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', path='f"{project_name}/{phase_name}"'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='planning_loop_id'
        ),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='planning_loop_id', feedback_markdown='feedback_markdown'
        ),
    )


def create_task_reviewer_agent_tools() -> TaskReviewerAgentTools:
    builder = TemplateToolBuilder()

    for tool in TaskReviewerAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in TaskReviewerAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    return TaskReviewerAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='planning_loop_id'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', path='f"{project_name}/{phase_name}"'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='coding_loop_id'
        ),
        store_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_CRITIC_FEEDBACK, loop_id='coding_loop_id', feedback_markdown='feedback_markdown'
        ),
    )


def create_task_coder_agent_tools(platform_tools: list[str]) -> TaskCoderAgentTools:
    builder = TemplateToolBuilder()

    for tool in TaskCoderAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    for builtin_tool, params in TaskCoderAgentTools.builtin_tools:
        builder.add_builtin_tool(builtin_tool, params)

    builder.add_platform_tools(platform_tools)

    return TaskCoderAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        update_task_status=platform_tools[0],
        retrieve_task=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"task"', loop_id='planning_loop_id'
        ),
        retrieve_phase=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_DOCUMENT, doc_type='"phase"', path='f"{project_name}/{phase_name}"'
        ),
        retrieve_feedback=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.GET_FEEDBACK, loop_id='coding_loop_id'
        ),
    )


def create_create_phase_agent_tools(platform_tools: list[str]) -> CreatePhaseAgentTools:
    builder = TemplateToolBuilder()

    for tool in CreatePhaseAgentTools.respec_ai_tools:
        builder.add_respec_ai_tool(tool)

    builder.add_platform_tools(platform_tools)

    return CreatePhaseAgentTools(
        tools_yaml=builder.render_comma_separated_tools(),
        create_phase_tool=platform_tools[0],
        get_phase_tool=platform_tools[1],
        update_phase_tool=platform_tools[2],
        get_roadmap=ToolDocGenerator.generate_tool_call_inline(RespecAITool.GET_ROADMAP, project_name='PROJECT_NAME'),
        store_document=ToolDocGenerator.generate_tool_call_inline(
            RespecAITool.STORE_DOCUMENT,
            doc_type='"phase"',
            path='f"{PROJECT_NAME}/{PHASE_NAME}"',
            content='extracted_phase_markdown',
        ),
    )
