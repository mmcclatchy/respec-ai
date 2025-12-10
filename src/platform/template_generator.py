from pathlib import Path

from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.platform.models import (
    TaskCoderAgentTools,
    CreatePhaseAgentTools,
    PlanRoadmapAgentTools,
    PhaseArchitectAgentTools,
    PhaseCriticAgentTools,
)
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import (
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
)
from src.platform.templates.agents import (
    generate_analyst_critic_template,
    generate_create_phase_template,
    generate_phase_architect_template,
    generate_phase_critic_template,
    generate_plan_analyst_template,
    generate_plan_critic_template,
    generate_roadmap_critic_template,
    generate_roadmap_template,
    generate_task_coder_template,
    generate_task_critic_template,
    generate_task_reviewer_template,
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
        CommandTemplate.PHASE,
        CommandTemplate.CODE,
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

    phase_tools = CreatePhaseAgentTools(
        create_phase_tool=tool_registry.get_tool_for_platform(AbstractOperation.CREATE_SPEC_TOOL.value, platform_type),
        get_phase_tool=tool_registry.get_tool_for_platform(AbstractOperation.GET_SPEC_TOOL.value, platform_type),
        update_phase_tool=tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform_type),
    )

    roadmap_tools = PlanRoadmapAgentTools(
        create_spec_external=tool_registry.get_tool_for_platform(
            AbstractOperation.CREATE_SPEC_TOOL.value, platform_type
        )
    )

    build_coder_tools = TaskCoderAgentTools(
        update_task_status=tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform_type)
    )

    spec_architect_tools = PhaseArchitectAgentTools(tools_yaml=create_phase_architect_agent_tools())
    spec_critic_tools = PhaseCriticAgentTools(
        tools_yaml=create_phase_critic_agent_tools(), phase_length_soft_cap=loop_config.phase_length_soft_cap
    )

    return [
        ('respec-plan-analyst', generate_plan_analyst_template()),
        ('respec-plan-critic', generate_plan_critic_template()),
        ('respec-analyst-critic', generate_analyst_critic_template()),
        ('respec-roadmap', generate_roadmap_template(roadmap_tools)),
        ('respec-roadmap-critic', generate_roadmap_critic_template()),
        ('respec-create-phase', generate_create_phase_template(phase_tools)),
        ('respec-phase-architect', generate_phase_architect_template(spec_architect_tools)),
        ('respec-phase-critic', generate_phase_critic_template(spec_critic_tools)),
        ('respec-task-critic', generate_task_critic_template()),
        ('respec-task-coder', generate_task_coder_template(build_coder_tools)),
        ('respec-task-reviewer', generate_task_reviewer_template()),
    ]
