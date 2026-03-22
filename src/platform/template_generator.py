from pathlib import Path

from fastmcp import FastMCP

from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.platform.models import (
    CodeCommandTools,
    PatchCommandTools,
    PhaseCommandTools,
    PlanCommandTools,
    PlanRoadmapCommandTools,
    TaskCommandTools,
)
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_helpers import (
    create_analyst_critic_agent_tools,
    create_automated_quality_checker_agent_tools,
    create_backend_api_reviewer_agent_tools,
    create_code_reviewer_agent_tools,
    create_coder_agent_tools,
    create_coding_standards_reviewer_agent_tools,
    create_create_phase_agent_tools,
    create_database_reviewer_agent_tools,
    create_frontend_reviewer_agent_tools,
    create_infrastructure_reviewer_agent_tools,
    create_patch_planner_agent_tools,
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
    create_plan_analyst_agent_tools,
    create_plan_critic_agent_tools,
    create_review_consolidator_agent_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
    create_task_critic_agent_tools,
    create_task_plan_critic_agent_tools,
    create_task_planner_agent_tools,
)
from src.platform.templates.agents import (
    generate_analyst_critic_template,
    generate_automated_quality_checker_template,
    generate_backend_api_reviewer_template,
    generate_code_reviewer_template,
    generate_coder_template,
    generate_coding_standards_reviewer_template,
    generate_create_phase_template,
    generate_database_reviewer_template,
    generate_frontend_reviewer_template,
    generate_infrastructure_reviewer_template,
    generate_patch_planner_template,
    generate_phase_architect_template,
    generate_phase_critic_template,
    generate_plan_analyst_template,
    generate_plan_critic_template,
    generate_review_consolidator_template,
    generate_roadmap_critic_template,
    generate_roadmap_template,
    generate_spec_alignment_reviewer_template,
    generate_task_critic_template,
    generate_task_plan_critic_template,
    generate_task_planner_template,
)
from src.platform.adapters import get_platform_adapter
from src.platform.tool_enums import RespecAICommand
from src.utils.setting_configs import loop_config


def generate_templates(
    orchestrator: PlatformOrchestrator,
    project_path: Path,
    platform_type: PlatformType,
    mcp: FastMCP | None = None,
) -> tuple[list[Path], int, int]:
    if mcp:
        PhaseCommandTools.initialize_tool_docs(mcp)
        PlanCommandTools.initialize_tool_docs(mcp)
        TaskCommandTools.initialize_tool_docs(mcp)
        CodeCommandTools.initialize_tool_docs(mcp)
        PatchCommandTools.initialize_tool_docs(mcp)
        PlanRoadmapCommandTools.initialize_tool_docs(mcp)

    commands_dir = get_commands_dir(project_path)
    agents_dir = get_agents_dir(project_path)

    commands_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    for stale in commands_dir.glob('respec-*.md'):
        stale.unlink()
    for stale in agents_dir.glob('respec-*.md'):
        stale.unlink()

    files_written: list[Path] = []

    command_templates = [
        RespecAICommand.PLAN,
        RespecAICommand.PHASE,
        RespecAICommand.TASK,
        RespecAICommand.CODE,
        RespecAICommand.PATCH,
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
    adapter = get_platform_adapter(platform_type)

    create_phase_platform_tools = [
        adapter.create_phase_tool,
        adapter.retrieve_phase_tool,
        adapter.update_phase_tool,
    ]

    coder_platform_tools = [
        adapter.update_phase_tool,
    ]

    plan_analyst_tools = create_plan_analyst_agent_tools()
    plan_critic_tools = create_plan_critic_agent_tools()
    analyst_critic_tools = create_analyst_critic_agent_tools()
    roadmap_tools = create_roadmap_agent_tools()
    roadmap_critic_tools = create_roadmap_critic_agent_tools()
    create_phase_tools = create_create_phase_agent_tools(create_phase_platform_tools, platform_type)
    phase_architect_tools = create_phase_architect_agent_tools()
    phase_critic_tools = create_phase_critic_agent_tools(loop_config.phase_length_soft_cap)
    task_planner_tools = create_task_planner_agent_tools()
    task_plan_critic_tools = create_task_plan_critic_agent_tools()
    patch_planner_tools = create_patch_planner_agent_tools()
    task_critic_tools = create_task_critic_agent_tools()
    coder_tools = create_coder_agent_tools(coder_platform_tools)
    code_reviewer_tools = create_code_reviewer_agent_tools()
    automated_quality_checker_tools = create_automated_quality_checker_agent_tools()
    spec_alignment_reviewer_tools = create_spec_alignment_reviewer_agent_tools()
    frontend_reviewer_tools = create_frontend_reviewer_agent_tools()
    backend_api_reviewer_tools = create_backend_api_reviewer_agent_tools()
    database_reviewer_tools = create_database_reviewer_agent_tools()
    infrastructure_reviewer_tools = create_infrastructure_reviewer_agent_tools()
    coding_standards_reviewer_tools = create_coding_standards_reviewer_agent_tools()
    review_consolidator_tools = create_review_consolidator_agent_tools()

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
        ('respec-patch-planner', generate_patch_planner_template(patch_planner_tools)),
        ('respec-task-critic', generate_task_critic_template(task_critic_tools)),
        ('respec-coder', generate_coder_template(coder_tools)),
        ('respec-code-reviewer', generate_code_reviewer_template(code_reviewer_tools)),
        (
            'respec-automated-quality-checker',
            generate_automated_quality_checker_template(automated_quality_checker_tools),
        ),
        ('respec-spec-alignment-reviewer', generate_spec_alignment_reviewer_template(spec_alignment_reviewer_tools)),
        ('respec-frontend-reviewer', generate_frontend_reviewer_template(frontend_reviewer_tools)),
        ('respec-backend-api-reviewer', generate_backend_api_reviewer_template(backend_api_reviewer_tools)),
        ('respec-database-reviewer', generate_database_reviewer_template(database_reviewer_tools)),
        ('respec-infrastructure-reviewer', generate_infrastructure_reviewer_template(infrastructure_reviewer_tools)),
        (
            'respec-coding-standards-reviewer',
            generate_coding_standards_reviewer_template(coding_standards_reviewer_tools),
        ),
        ('respec-review-consolidator', generate_review_consolidator_template(review_consolidator_tools)),
    ]
