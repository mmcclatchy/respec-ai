from pathlib import Path

from fastmcp import FastMCP

from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.platform.models import (
    CodeCommandTools,
    PhaseCommandTools,
    PlanCommandTools,
    PlanRoadmapCommandTools,
    TaskCommandTools,
)
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import (
    create_analyst_critic_agent_tools,
    create_create_phase_agent_tools,
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
    create_plan_analyst_agent_tools,
    create_plan_critic_agent_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
    create_task_coder_agent_tools,
    create_task_critic_agent_tools,
    create_task_plan_critic_agent_tools,
    create_task_planner_agent_tools,
    create_task_reviewer_agent_tools,
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
    generate_task_plan_critic_template,
    generate_task_planner_template,
    generate_task_reviewer_template,
)
from src.platform.tool_enums import AbstractOperation, RespecAICommand
from src.platform.tool_registry import ToolRegistry
from src.utils.setting_configs import loop_config


def generate_templates(
    orchestrator: PlatformOrchestrator,
    project_path: Path,
    platform_type: PlatformType,
    mcp: FastMCP | None = None,
) -> tuple[list[Path], int, int]:
    """Generate command and agent templates for a project.

    Args:
        orchestrator: Platform orchestrator instance
        project_path: Plan root directory
        platform_type: Platform type (linear, github, markdown)
        mcp: Optional FastMCP instance for tool documentation extraction

    Returns:
        Tuple of (files_written, commands_count, agents_count)
    """
    if mcp:
        PhaseCommandTools.initialize_tool_docs(mcp)
        PlanCommandTools.initialize_tool_docs(mcp)
        TaskCommandTools.initialize_tool_docs(mcp)
        CodeCommandTools.initialize_tool_docs(mcp)
        PlanRoadmapCommandTools.initialize_tool_docs(mcp)

    commands_dir = get_commands_dir(project_path)
    agents_dir = get_agents_dir(project_path)

    commands_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[Path] = []

    command_templates = [
        RespecAICommand.PLAN,
        RespecAICommand.PHASE,
        RespecAICommand.TASK,
        RespecAICommand.CODE,
        RespecAICommand.ROADMAP,
        RespecAICommand.PLAN_CONVERSATION,
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

    create_phase_platform_tools = [
        tool_registry.get_tool_for_platform(AbstractOperation.CREATE_PHASE_TOOL, platform_type),
        tool_registry.get_tool_for_platform(AbstractOperation.GET_PHASE_TOOL, platform_type),
        tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_PHASE_TOOL, platform_type),
    ]

    task_coder_platform_tools = [
        tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_PHASE_TOOL, platform_type),
    ]

    plan_analyst_tools = create_plan_analyst_agent_tools()
    plan_critic_tools = create_plan_critic_agent_tools()
    analyst_critic_tools = create_analyst_critic_agent_tools()
    roadmap_tools = create_roadmap_agent_tools()
    roadmap_critic_tools = create_roadmap_critic_agent_tools()
    create_phase_tools = create_create_phase_agent_tools(create_phase_platform_tools)
    phase_architect_tools = create_phase_architect_agent_tools()
    phase_critic_tools = create_phase_critic_agent_tools(loop_config.phase_length_soft_cap)
    task_planner_tools = create_task_planner_agent_tools()
    task_plan_critic_tools = create_task_plan_critic_agent_tools()
    task_critic_tools = create_task_critic_agent_tools()
    task_coder_tools = create_task_coder_agent_tools(task_coder_platform_tools)
    task_reviewer_tools = create_task_reviewer_agent_tools()

    return [
        ('respec-plan-analyst', generate_plan_analyst_template(plan_analyst_tools)),
        ('respec-plan-critic', generate_plan_critic_template(plan_critic_tools)),
        ('respec-analyst-critic', generate_analyst_critic_template(analyst_critic_tools)),
        ('respec-roadmap', generate_roadmap_template(roadmap_tools)),
        ('respec-roadmap-critic', generate_roadmap_critic_template(roadmap_critic_tools)),
        ('respec-create-phase', generate_create_phase_template(create_phase_tools)),
        ('respec-phase-architect', generate_phase_architect_template(phase_architect_tools)),
        ('respec-phase-critic', generate_phase_critic_template(phase_critic_tools)),
        ('respec-task-planner', generate_task_planner_template(task_planner_tools)),
        ('respec-task-plan-critic', generate_task_plan_critic_template(task_plan_critic_tools)),
        ('respec-task-critic', generate_task_critic_template(task_critic_tools)),
        ('respec-task-coder', generate_task_coder_template(task_coder_tools)),
        ('respec-task-reviewer', generate_task_reviewer_template(task_reviewer_tools)),
    ]
