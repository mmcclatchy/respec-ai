from .models import ToolReference
from .tool_enums import BuiltInTool, SpecterMCPTool


class TemplateToolBuilder:
    def __init__(self) -> None:
        self.tools: list[ToolReference] = []

    def add_task_agent(self, agent_name: str) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInTool.TASK, parameters=agent_name))
        return self

    def add_bash_script(self, script_path: str) -> 'TemplateToolBuilder':
        self.tools.append(ToolReference(tool=BuiltInTool.BASH, parameters=script_path))
        return self

    def add_specter_tool(self, tool: SpecterMCPTool) -> 'TemplateToolBuilder':
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
        .add_task_agent('specter-spec-architect')
        .add_task_agent('specter-spec-critic')
        .add_task_agent('specter-plan-analyst')
        .add_bash_script('~/.claude/scripts/research-advisor-archive-scan.sh:*')
        .add_specter_tool(SpecterMCPTool.INITIALIZE_REFINEMENT_LOOP)
        .add_specter_tool(SpecterMCPTool.DECIDE_LOOP_NEXT_ACTION)
        .add_specter_tool(SpecterMCPTool.GET_LOOP_STATUS)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_plan_command_tools(platform_tools: list[str]) -> str:
    """Create validated tool list for plan command.

    Note: Some conversation context tools referenced in plan_command.py are not yet
    defined in SpecterMCPTool enum and need to be added.
    """
    builder = (
        TemplateToolBuilder()
        .add_task_agent('specter-plan-conversation')
        .add_task_agent('specter-plan-critic')
        .add_task_agent('specter-plan-analyst')
        .add_task_agent('specter-analyst-critic')
        .add_specter_tool(SpecterMCPTool.INITIALIZE_REFINEMENT_LOOP)
        .add_specter_tool(SpecterMCPTool.DECIDE_LOOP_NEXT_ACTION)
        .add_specter_tool(SpecterMCPTool.GET_PREVIOUS_OBJECTIVE_FEEDBACK)
        .add_specter_tool(SpecterMCPTool.STORE_CURRENT_OBJECTIVE_FEEDBACK)
        .add_specter_tool(SpecterMCPTool.STORE_PROJECT_PLAN)
        .add_specter_tool(SpecterMCPTool.GET_PROJECT_PLAN_MARKDOWN)
        .add_specter_tool(SpecterMCPTool.STORE_CRITIC_FEEDBACK)
        .add_specter_tool(SpecterMCPTool.GET_FEEDBACK)
        .add_specter_tool(SpecterMCPTool.STORE_CURRENT_ANALYSIS)
        .add_specter_tool(SpecterMCPTool.GET_PREVIOUS_ANALYSIS)
        .add_specter_tool(SpecterMCPTool.CREATE_PLAN_COMPLETION_REPORT)
        .add_specter_tool(SpecterMCPTool.STORE_PLAN_COMPLETION_REPORT)
        .add_specter_tool(SpecterMCPTool.GET_PLAN_COMPLETION_REPORT_MARKDOWN)
        .add_specter_tool(SpecterMCPTool.UPDATE_PLAN_COMPLETION_REPORT)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_build_command_tools(platform_tools: list[str]) -> str:
    builder = (
        TemplateToolBuilder()
        .add_task_agent('specter-build-planner')
        .add_task_agent('specter-build-critic')
        .add_task_agent('specter-build-coder')
        .add_task_agent('specter-build-reviewer')
        .add_task_agent('specter-research-synthesizer')
        .add_bash_script('~/.claude/scripts/detect-packages.sh:*')
        .add_specter_tool(SpecterMCPTool.INITIALIZE_REFINEMENT_LOOP)
        .add_specter_tool(SpecterMCPTool.DECIDE_LOOP_NEXT_ACTION)
        .add_specter_tool(SpecterMCPTool.GET_LOOP_STATUS)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_roadmap_tools(platform_tools: list[str]) -> str:
    builder = (
        TemplateToolBuilder()
        .add_task_agent('specter-roadmap')
        .add_task_agent('specter-roadmap-critic')
        .add_task_agent('specter-create-spec')
        .add_specter_tool(SpecterMCPTool.INITIALIZE_REFINEMENT_LOOP)
        .add_specter_tool(SpecterMCPTool.DECIDE_LOOP_NEXT_ACTION)
        .add_specter_tool(SpecterMCPTool.GET_LOOP_STATUS)
        .add_specter_tool(SpecterMCPTool.CREATE_ROADMAP)
        .add_specter_tool(SpecterMCPTool.GET_ROADMAP)
        .add_specter_tool(SpecterMCPTool.STORE_SPEC)
        .add_specter_tool(SpecterMCPTool.GET_SPEC_MARKDOWN)
        .add_specter_tool(SpecterMCPTool.LIST_SPECS)
        .add_platform_tools(platform_tools)
    )

    return builder.render_comma_separated_tools()


def create_spec_architect_agent_tools() -> str:
    builder = (
        TemplateToolBuilder()
        .add_specter_tool(SpecterMCPTool.GET_SPEC_MARKDOWN)
        .add_specter_tool(SpecterMCPTool.STORE_SPEC)
        .add_specter_tool(SpecterMCPTool.LINK_LOOP_TO_SPEC)
        .add_specter_tool(SpecterMCPTool.GET_FEEDBACK)
        .add_builtin_tool(BuiltInTool.READ)
        .add_builtin_tool(BuiltInTool.BASH, '~/.claude/scripts/research-advisor-archive-scan.sh:*')
        .add_builtin_tool(BuiltInTool.GREP)
        .add_builtin_tool(BuiltInTool.GLOB)
    )
    return builder.render_comma_separated_tools()


def create_spec_critic_agent_tools() -> str:
    builder = (
        TemplateToolBuilder()
        .add_specter_tool(SpecterMCPTool.GET_SPEC_MARKDOWN)
        .add_specter_tool(SpecterMCPTool.GET_FEEDBACK)
        .add_specter_tool(SpecterMCPTool.STORE_CRITIC_FEEDBACK)
    )
    return builder.render_comma_separated_tools()
