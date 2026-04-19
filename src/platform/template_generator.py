from pathlib import Path

from fastmcp import FastMCP

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
    create_coder_agent_tools,
    create_coding_standards_reviewer_agent_tools,
    create_create_phase_agent_tools,
    create_database_reviewer_agent_tools,
    create_frontend_reviewer_agent_tools,
    create_infrastructure_reviewer_agent_tools,
    create_patch_planner_agent_tools,
    create_code_quality_reviewer_agent_tools,
    create_phase_architect_agent_tools,
    create_phase_critic_agent_tools,
    create_plan_analyst_agent_tools,
    create_plan_critic_agent_tools,
    create_review_consolidator_agent_tools,
    create_roadmap_agent_tools,
    create_roadmap_critic_agent_tools,
    create_spec_alignment_reviewer_agent_tools,
    create_task_plan_critic_agent_tools,
    create_task_planner_agent_tools,
)
from src.platform.templates.agents import (
    generate_analyst_critic_template,
    generate_automated_quality_checker_template,
    generate_backend_api_reviewer_template,
    generate_code_quality_reviewer_template,
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
    generate_task_plan_critic_template,
    generate_task_planner_template,
)
from src.platform.adapters import get_platform_adapter
from src.platform.tui_adapters import AgentSpec, CommandSpec, get_tui_adapter
from src.platform.tui_adapters.base import TuiAdapter
from src.platform.tui_selector import TuiType
from src.platform.tool_enums import RespecAICommand
from src.utils.setting_configs import loop_config


_COMMAND_TEMPLATES = [
    RespecAICommand.PLAN,
    RespecAICommand.PHASE,
    RespecAICommand.TASK,
    RespecAICommand.CODE,
    RespecAICommand.PATCH,
    RespecAICommand.ROADMAP,
    RespecAICommand.PLAN_CONVERSATION,
    RespecAICommand.STANDARDS,
]

_COMMAND_CATEGORY_BY_NAME: dict[RespecAICommand, str] = {
    RespecAICommand.PLAN: 'reasoning',
    RespecAICommand.PLAN_CONVERSATION: 'reasoning',
    RespecAICommand.PHASE: 'orchestration',
    RespecAICommand.TASK: 'orchestration',
    RespecAICommand.CODE: 'orchestration',
    RespecAICommand.PATCH: 'orchestration',
    RespecAICommand.ROADMAP: 'orchestration',
    RespecAICommand.STANDARDS: 'orchestration',
}

_AGENT_NAMES = [
    'respec-plan-analyst',
    'respec-plan-critic',
    'respec-analyst-critic',
    'respec-roadmap',
    'respec-roadmap-critic',
    'respec-create-phase',
    'respec-phase-architect',
    'respec-phase-critic',
    'respec-task-planner',
    'respec-task-plan-critic',
    'respec-patch-planner',
    'respec-coder',
    'respec-automated-quality-checker',
    'respec-code-quality-reviewer',
    'respec-spec-alignment-reviewer',
    'respec-frontend-reviewer',
    'respec-backend-api-reviewer',
    'respec-database-reviewer',
    'respec-infrastructure-reviewer',
    'respec-coding-standards-reviewer',
    'respec-review-consolidator',
]

EXPECTED_COMMANDS_COUNT = len(_COMMAND_TEMPLATES)
EXPECTED_AGENTS_COUNT = len(_AGENT_NAMES)


def generate_templates(
    orchestrator: PlatformOrchestrator,
    project_path: Path,
    platform_type: PlatformType,
    mcp: FastMCP | None = None,
    tui_adapter: TuiAdapter | None = None,
) -> tuple[list[Path], int, int]:
    if mcp:
        PhaseCommandTools.initialize_tool_docs(mcp)
        PlanCommandTools.initialize_tool_docs(mcp)
        TaskCommandTools.initialize_tool_docs(mcp)
        CodeCommandTools.initialize_tool_docs(mcp)
        PatchCommandTools.initialize_tool_docs(mcp)
        PlanRoadmapCommandTools.initialize_tool_docs(mcp)

    adapter = tui_adapter or get_tui_adapter(TuiType.CLAUDE_CODE)
    plans_dir = adapter.plans_dir()

    commands: list[CommandSpec] = [
        _parse_command_spec(
            cmd,
            orchestrator.template_coordinator.generate_command_template(
                cmd, platform_type, plans_dir=plans_dir, tui_adapter=adapter
            ),
            model=_resolve_model_for_category(adapter, _COMMAND_CATEGORY_BY_NAME[cmd]),
        )
        for cmd in _COMMAND_TEMPLATES
    ]

    agents: list[AgentSpec] = _get_agent_specs(adapter, platform_type, plans_dir=plans_dir)

    files_written = adapter.write_all(project_path, agents, commands)

    return files_written, len(commands), len(agents)


def _resolve_model_for_category(adapter: TuiAdapter, category: str) -> str:
    if category == 'reasoning':
        return adapter.reasoning_model
    if category == 'orchestration':
        return adapter.orchestration_model
    if category == 'coding':
        return adapter.coding_model
    if category == 'review':
        return adapter.review_model
    raise ValueError(f'Unknown model category: {category}')


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    separator = '---\n\n'
    if separator not in content:
        return {}, content
    idx = content.index(separator)
    fm_block = content[:idx]
    body = content[idx + len(separator) :]
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ': ' in line:
            k, v = line.split(': ', 1)
            fm[k.strip()] = v.strip()
    return fm, body


def _parse_agent_spec(name: str, content: str) -> AgentSpec:
    fm, body = _parse_frontmatter(content)
    tools = [t.strip() for t in fm.get('tools', '').split(', ') if t.strip()]
    return AgentSpec(
        name=fm.get('name', name),
        description=fm.get('description', ''),
        model=fm.get('model', 'sonnet'),
        tools=tools,
        body=body,
        color=fm.get('color'),
        is_orchestrator=False,
    )


def _parse_command_spec(cmd: RespecAICommand, content: str, model: str) -> CommandSpec:
    fm, body = _parse_frontmatter(content)
    tools = [t.strip() for t in fm.get('allowed-tools', '').split(', ') if t.strip()]
    delegated_agents = [t[5:-1] for t in tools if t.startswith('Task(') and t.endswith(')')]
    return CommandSpec(
        name=cmd.value,
        description=fm.get('description', ''),
        argument_hint=fm.get('argument-hint', ''),
        tools=tools,
        body=body,
        delegated_agents=delegated_agents,
        model=model,
    )


def _get_agent_specs(
    tui_adapter: TuiAdapter, platform_type: PlatformType, plans_dir: str = '~/.claude/plans'
) -> list[AgentSpec]:
    platform_adapter = get_platform_adapter(platform_type)

    create_phase_platform_tools = [
        platform_adapter.create_phase_tool,
        platform_adapter.retrieve_phase_tool,
        platform_adapter.update_phase_tool,
    ]

    coder_platform_tools = [
        platform_adapter.update_phase_tool,
    ]

    plan_analyst_tools = create_plan_analyst_agent_tools(tui_adapter)
    plan_critic_tools = create_plan_critic_agent_tools(tui_adapter)
    analyst_critic_tools = create_analyst_critic_agent_tools(tui_adapter)
    roadmap_tools = create_roadmap_agent_tools(tui_adapter, plans_dir=plans_dir)
    roadmap_critic_tools = create_roadmap_critic_agent_tools(tui_adapter)
    create_phase_tools = create_create_phase_agent_tools(tui_adapter, create_phase_platform_tools, platform_type)
    phase_architect_tools = create_phase_architect_agent_tools(tui_adapter, plans_dir=plans_dir)
    phase_critic_tools = create_phase_critic_agent_tools(tui_adapter, loop_config.phase_length_soft_cap)
    task_planner_tools = create_task_planner_agent_tools(tui_adapter)
    task_plan_critic_tools = create_task_plan_critic_agent_tools(tui_adapter)
    patch_planner_tools = create_patch_planner_agent_tools(tui_adapter)
    coder_tools = create_coder_agent_tools(tui_adapter, coder_platform_tools)
    automated_quality_checker_tools = create_automated_quality_checker_agent_tools(tui_adapter)
    code_quality_reviewer_tools = create_code_quality_reviewer_agent_tools(tui_adapter)
    spec_alignment_reviewer_tools = create_spec_alignment_reviewer_agent_tools(tui_adapter)
    frontend_reviewer_tools = create_frontend_reviewer_agent_tools(tui_adapter)
    backend_api_reviewer_tools = create_backend_api_reviewer_agent_tools(tui_adapter)
    database_reviewer_tools = create_database_reviewer_agent_tools(tui_adapter)
    infrastructure_reviewer_tools = create_infrastructure_reviewer_agent_tools(tui_adapter)
    coding_standards_reviewer_tools = create_coding_standards_reviewer_agent_tools(tui_adapter)
    review_consolidator_tools = create_review_consolidator_agent_tools(tui_adapter)

    return [
        _parse_agent_spec('respec-plan-analyst', generate_plan_analyst_template(plan_analyst_tools)),
        _parse_agent_spec('respec-plan-critic', generate_plan_critic_template(plan_critic_tools)),
        _parse_agent_spec('respec-analyst-critic', generate_analyst_critic_template(analyst_critic_tools)),
        _parse_agent_spec('respec-roadmap', generate_roadmap_template(roadmap_tools)),
        _parse_agent_spec('respec-roadmap-critic', generate_roadmap_critic_template(roadmap_critic_tools)),
        _parse_agent_spec('respec-create-phase', generate_create_phase_template(create_phase_tools)),
        _parse_agent_spec('respec-phase-architect', generate_phase_architect_template(phase_architect_tools)),
        _parse_agent_spec('respec-phase-critic', generate_phase_critic_template(phase_critic_tools)),
        _parse_agent_spec('respec-task-planner', generate_task_planner_template(task_planner_tools)),
        _parse_agent_spec('respec-task-plan-critic', generate_task_plan_critic_template(task_plan_critic_tools)),
        _parse_agent_spec('respec-patch-planner', generate_patch_planner_template(patch_planner_tools)),
        _parse_agent_spec('respec-coder', generate_coder_template(coder_tools)),
        _parse_agent_spec(
            'respec-automated-quality-checker',
            generate_automated_quality_checker_template(automated_quality_checker_tools),
        ),
        _parse_agent_spec(
            'respec-code-quality-reviewer', generate_code_quality_reviewer_template(code_quality_reviewer_tools)
        ),
        _parse_agent_spec(
            'respec-spec-alignment-reviewer', generate_spec_alignment_reviewer_template(spec_alignment_reviewer_tools)
        ),
        _parse_agent_spec('respec-frontend-reviewer', generate_frontend_reviewer_template(frontend_reviewer_tools)),
        _parse_agent_spec(
            'respec-backend-api-reviewer', generate_backend_api_reviewer_template(backend_api_reviewer_tools)
        ),
        _parse_agent_spec('respec-database-reviewer', generate_database_reviewer_template(database_reviewer_tools)),
        _parse_agent_spec(
            'respec-infrastructure-reviewer', generate_infrastructure_reviewer_template(infrastructure_reviewer_tools)
        ),
        _parse_agent_spec(
            'respec-coding-standards-reviewer',
            generate_coding_standards_reviewer_template(coding_standards_reviewer_tools),
        ),
        _parse_agent_spec(
            'respec-review-consolidator', generate_review_consolidator_template(review_consolidator_tools)
        ),
    ]
