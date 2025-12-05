from .models import ToolReference
from .tool_enums import BuiltInTool, RespecAITool


class TemplateToolBuilder:
    def __init__(self) -> None:
        self.tools: list[ToolReference] = []

    def add_task_agent(self, agent_name: str) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInTool.TASK, parameters=agent_name))
        return self

    def add_bash_script(self, script_path: str) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInTool.BASH, parameters=script_path))
        return self

    def add_reRESPEC_AI_tool(self, tool: RespecAITool) -> 'TemplateToolBuilder':
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


def create_spec_command_tools(platform_tools: list[str]) -> str:
    builder = (
        TemplateToolBuilder()
        .add_task_agent('respec-spec-architect')
        .add_task_agent('respec-spec-critic')
        .add_bash_script('~/.claude/scripts/research-advisor-archive-scan.sh:*')
        .add_reRESPEC_AI_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
        .add_reRESPEC_AI_tool(RespecAITool.DECIDE_LOOP_NEXT_ACTION)
        .add_reRESPEC_AI_tool(RespecAITool.GET_LOOP_STATUS)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_plan_command_tools(platform_tools: list[str]) -> str:
    """Create validated tool list for plan command.

    Note: Some conversation context tools referenced in plan_command.py are not yet
    defined in RespecAITool enum and need to be added.
    """
    builder = (
        TemplateToolBuilder()
        .add_task_agent('respec-plan-conversation')
        .add_task_agent('respec-plan-critic')
        .add_task_agent('respec-plan-analyst')
        .add_task_agent('respec-analyst-critic')
        .add_reRESPEC_AI_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
        .add_reRESPEC_AI_tool(RespecAITool.DECIDE_LOOP_NEXT_ACTION)
        .add_reRESPEC_AI_tool(RespecAITool.GET_PREVIOUS_OBJECTIVE_FEEDBACK)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_CURRENT_OBJECTIVE_FEEDBACK)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_PROJECT_PLAN)
        .add_reRESPEC_AI_tool(RespecAITool.GET_PROJECT_PLAN_MARKDOWN)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_CRITIC_FEEDBACK)
        .add_reRESPEC_AI_tool(RespecAITool.GET_FEEDBACK)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_CURRENT_ANALYSIS)
        .add_reRESPEC_AI_tool(RespecAITool.GET_PREVIOUS_ANALYSIS)
        .add_reRESPEC_AI_tool(RespecAITool.CREATE_PLAN_COMPLETION_REPORT)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_PLAN_COMPLETION_REPORT)
        .add_reRESPEC_AI_tool(RespecAITool.GET_PLAN_COMPLETION_REPORT_MARKDOWN)
        .add_reRESPEC_AI_tool(RespecAITool.UPDATE_PLAN_COMPLETION_REPORT)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_build_command_tools(platform_tools: list[str]) -> str:
    builder = (
        TemplateToolBuilder()
        .add_task_agent('respec-build-planner')
        .add_task_agent('respec-build-critic')
        .add_task_agent('respec-build-coder')
        .add_task_agent('respec-build-reviewer')
        .add_task_agent('respec-research-synthesizer')
        .add_bash_script('~/.claude/scripts/detect-packages.sh:*')
        .add_reRESPEC_AI_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
        .add_reRESPEC_AI_tool(RespecAITool.DECIDE_LOOP_NEXT_ACTION)
        .add_reRESPEC_AI_tool(RespecAITool.GET_LOOP_STATUS)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_roadmap_tools(platform_tools: list[str]) -> str:
    builder = (
        TemplateToolBuilder()
        .add_task_agent('respec-roadmap')
        .add_task_agent('respec-roadmap-critic')
        .add_task_agent('respec-create-spec')
        .add_reRESPEC_AI_tool(RespecAITool.INITIALIZE_REFINEMENT_LOOP)
        .add_reRESPEC_AI_tool(RespecAITool.DECIDE_LOOP_NEXT_ACTION)
        .add_reRESPEC_AI_tool(RespecAITool.GET_LOOP_STATUS)
        .add_reRESPEC_AI_tool(RespecAITool.CREATE_ROADMAP)
        .add_reRESPEC_AI_tool(RespecAITool.GET_ROADMAP)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_SPEC)
        .add_reRESPEC_AI_tool(RespecAITool.GET_SPEC_MARKDOWN)
        .add_reRESPEC_AI_tool(RespecAITool.LIST_SPECS)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_spec_architect_agent_tools() -> str:
    builder = (
        TemplateToolBuilder()
        .add_reRESPEC_AI_tool(RespecAITool.GET_SPEC_MARKDOWN)
        .add_reRESPEC_AI_tool(RespecAITool.UPDATE_SPEC)
        .add_reRESPEC_AI_tool(RespecAITool.LINK_LOOP_TO_SPEC)
        .add_reRESPEC_AI_tool(RespecAITool.GET_FEEDBACK)
        .add_builtin_tool(BuiltInTool.READ)
        .add_builtin_tool(BuiltInTool.BASH, '~/.claude/scripts/research-advisor-archive-scan.sh:*')
        .add_builtin_tool(BuiltInTool.GREP)
        .add_builtin_tool(BuiltInTool.GLOB)
    )
    return builder.render_comma_separated_tools()


def create_spec_critic_agent_tools() -> str:
    builder = (
        TemplateToolBuilder()
        .add_reRESPEC_AI_tool(RespecAITool.GET_SPEC_MARKDOWN)
        .add_reRESPEC_AI_tool(RespecAITool.GET_FEEDBACK)
        .add_reRESPEC_AI_tool(RespecAITool.STORE_CRITIC_FEEDBACK)
    )
    return builder.render_comma_separated_tools()
