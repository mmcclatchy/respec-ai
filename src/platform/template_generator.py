from pathlib import Path

from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.platform.models import (
    BuildCoderAgentTools,
    CreateSpecAgentTools,
    PlanRoadmapAgentTools,
    SpecArchitectAgentTools,
    SpecCriticAgentTools,
)
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import (
    create_spec_architect_agent_tools,
    create_spec_critic_agent_tools,
)
from src.platform.templates.agents import (
    generate_analyst_critic_template,
    generate_build_coder_template,
    generate_build_critic_template,
    generate_build_planner_template,
    generate_build_reviewer_template,
    generate_create_spec_template,
    generate_plan_analyst_template,
    generate_plan_critic_template,
    generate_roadmap_critic_template,
    generate_roadmap_template,
    generate_spec_architect_template,
    generate_spec_critic_template,
)
from src.platform.tool_enums import AbstractOperation, CommandTemplate
from src.platform.tool_registry import ToolRegistry
from src.utils.setting_configs import loop_config


def generate_templates(
    orchestrator: PlatformOrchestrator,
    project_path: Path,
    platform_type: PlatformType,
) -> tuple[list[Path], int, int]:
    """Generate command and agent templates for a project.

    Args:
        orchestrator: Platform orchestrator instance
        project_path: Project root directory
        platform_type: Platform type (linear, github, markdown)

    Returns:
        Tuple of (files_written, commands_count, agents_count)
    """
    commands_dir = get_commands_dir(project_path)
    agents_dir = get_agents_dir(project_path)

    commands_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[Path] = []

    command_templates = [
        CommandTemplate.PLAN,
        CommandTemplate.SPEC,
        CommandTemplate.BUILD,
        CommandTemplate.ROADMAP,
        CommandTemplate.PLAN_CONVERSATION,
    ]

    for cmd in command_templates:
        content = orchestrator.template_coordinator.generate_command_template(cmd, platform_type)
        file_path = commands_dir / f'{cmd.value}.md'
        file_path.write_text(content, encoding='utf-8')
        files_written.append(file_path)

    agent_generators = _get_agent_generators(orchestrator, platform_type)

    for agent_name, content in agent_generators:
        file_path = agents_dir / f'{agent_name}.md'
        file_path.write_text(content, encoding='utf-8')
        files_written.append(file_path)

    commands_count = len(command_templates)
    agents_count = len(agent_generators)

    return files_written, commands_count, agents_count


def _get_agent_generators(
    orchestrator: PlatformOrchestrator,
    platform_type: PlatformType,
) -> list[tuple[str, str]]:
    tool_registry = ToolRegistry()

    spec_tools = CreateSpecAgentTools(
        create_spec_tool=tool_registry.get_tool_for_platform(AbstractOperation.CREATE_SPEC_TOOL.value, platform_type),
        get_spec_tool=tool_registry.get_tool_for_platform(AbstractOperation.GET_SPEC_TOOL.value, platform_type),
        update_spec_tool=tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform_type),
    )

    roadmap_tools = PlanRoadmapAgentTools(
        create_spec_external=tool_registry.get_tool_for_platform(
            AbstractOperation.CREATE_SPEC_TOOL.value, platform_type
        )
    )

    build_coder_tools = BuildCoderAgentTools(
        update_task_status=tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform_type)
    )

    spec_architect_tools = SpecArchitectAgentTools(tools_yaml=create_spec_architect_agent_tools())
    spec_critic_tools = SpecCriticAgentTools(
        tools_yaml=create_spec_critic_agent_tools(), spec_length_soft_cap=loop_config.spec_length_soft_cap
    )

    return [
        ('respec-plan-analyst', generate_plan_analyst_template()),
        ('respec-plan-critic', generate_plan_critic_template()),
        ('respec-analyst-critic', generate_analyst_critic_template()),
        ('respec-roadmap', generate_roadmap_template(roadmap_tools)),
        ('respec-roadmap-critic', generate_roadmap_critic_template()),
        ('respec-create-spec', generate_create_spec_template(spec_tools)),
        ('respec-spec-architect', generate_spec_architect_template(spec_architect_tools)),
        ('respec-spec-critic', generate_spec_critic_template(spec_critic_tools)),
        ('respec-build-planner', generate_build_planner_template()),
        ('respec-build-critic', generate_build_critic_template()),
        ('respec-build-coder', generate_build_coder_template(build_coder_tools)),
        ('respec-build-reviewer', generate_build_reviewer_template()),
    ]
