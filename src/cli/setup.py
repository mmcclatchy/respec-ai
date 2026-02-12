#!/usr/bin/env python3
"""CLI for setting up respec-ai in projects.

This CLI is called by install-respec-ai.sh to generate platform-specific
workflow files directly, eliminating the need for the /init-respec-ai command.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from src.platform.models import LanguageTooling, ProjectStack
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.tooling_defaults import detect_project_stack, detect_project_tooling
from src.platform.template_helpers import (
    create_analyst_critic_agent_tools,
    create_automated_quality_checker_agent_tools,
    create_backend_api_reviewer_agent_tools,
    create_code_reviewer_agent_tools,
    create_coder_agent_tools,
    create_create_phase_agent_tools,
    create_database_reviewer_agent_tools,
    create_frontend_reviewer_agent_tools,
    create_infrastructure_reviewer_agent_tools,
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
    generate_create_phase_template,
    generate_database_reviewer_template,
    generate_frontend_reviewer_template,
    generate_infrastructure_reviewer_template,
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
from src.platform.tool_enums import RespecAICommand
from src.platform.adapters import get_platform_adapter
from src.utils.setting_configs import loop_config


def setup_project(project_path: str, platform: Literal['linear', 'github', 'markdown'], plan_name: str) -> int:
    """Set up respec-ai workflow files for a project.

    Args:
        project_path: Absolute path to project directory
        platform: Platform type (linear, github, or markdown)
        plan_name: Name for this project

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        project = Path(project_path).resolve()

        if not project.exists():
            print(f'❌ Error: Plan directory does not exist: {project}', file=sys.stderr)
            return 1

        platform_type = PlatformType(platform)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        (project / '.claude' / 'commands').mkdir(parents=True, exist_ok=True)
        (project / '.claude' / 'agents').mkdir(parents=True, exist_ok=True)
        (project / '.respec-ai').mkdir(parents=True, exist_ok=True)

        files_written: list[str] = []

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
            file_path = project / '.claude' / 'commands' / f'{cmd.value}.md'
            file_path.write_text(content, encoding='utf-8')
            files_written.append(str(file_path.relative_to(project)))

        tooling = detect_project_tooling(project)
        if tooling:
            print(f'\nTooling configured for: {", ".join(tooling.keys())}')
            print('Edit .respec-ai/config.json to customize tool commands.')
        else:
            print('\nNo build files detected. Tooling section skipped.')
            print('Add tooling manually to .respec-ai/config.json if needed.')

        stack = detect_project_stack(project)
        stack_fields = stack.model_dump(exclude_none=True)
        if stack_fields:
            print(f'\nStack detected: {", ".join(f"{k}={v}" for k, v in stack_fields.items())}')

        agent_generators = _get_agent_generators(orchestrator, platform_type, tooling, stack)

        for agent_name, content in agent_generators:
            file_path = project / '.claude' / 'agents' / f'{agent_name}.md'
            file_path.write_text(content, encoding='utf-8')
            files_written.append(str(file_path.relative_to(project)))

        config: dict[str, Any] = {
            'plan_name': plan_name,
            'platform': platform,
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
        }
        if tooling:
            config['tooling'] = {lang: lang_tools.model_dump() for lang, lang_tools in tooling.items()}
        if stack_fields:
            config['stack'] = stack_fields
        config_path = project / '.respec-ai' / 'config.json'
        config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        files_written.append(str(config_path.relative_to(project)))

        print('✅ respec-ai setup complete!')
        print(f'\nPlatform: {platform}')
        print(f'Files Created: {len(files_written)}')
        print(f'Location: {project}')
        print('\n⚠️  IMPORTANT: Restart Claude Code to activate the new commands!')
        print('\nAvailable Commands (after restart):')
        print('  • /respec-plan - Create strategic plans')
        print('  • /respec-phase - Transform plans into technical specifications')
        print('  • /respec-code - Execute implementation workflows')
        print('  • /respec-roadmap - Create phased roadmaps')
        print('  • /respec-plan-conversation - Convert conversations into plans')
        print('\n🚀 Ready to begin! Restart Claude Code to use the respec-ai commands.')

        return 0

    except ValueError:
        print(f'❌ Error: Invalid platform "{platform}". Must be: linear, github, or markdown', file=sys.stderr)
        return 1
    except Exception as e:
        print(f'❌ Error: Setup failed: {e}', file=sys.stderr)
        return 1


def _get_agent_generators(
    orchestrator: PlatformOrchestrator,
    platform_type: PlatformType,
    tooling: dict[str, LanguageTooling] | None = None,
    stack: ProjectStack = ProjectStack(),
) -> list[tuple[str, str]]:
    adapter = get_platform_adapter(platform_type)

    create_phase_platform_tools = [
        adapter.create_phase_tool,
        adapter.retrieve_phase_tool,
        adapter.update_phase_tool,
    ]

    coder_platform_tools = [adapter.update_phase_tool]

    plan_analyst_tools = create_plan_analyst_agent_tools()
    plan_critic_tools = create_plan_critic_agent_tools()
    analyst_critic_tools = create_analyst_critic_agent_tools()
    roadmap_tools = create_roadmap_agent_tools()
    roadmap_critic_tools = create_roadmap_critic_agent_tools()
    create_phase_tools = create_create_phase_agent_tools(create_phase_platform_tools, platform_type)
    phase_architect_tools = create_phase_architect_agent_tools(stack=stack)
    phase_critic_tools = create_phase_critic_agent_tools(phase_length_soft_cap=loop_config.phase_length_soft_cap)
    task_planner_tools = create_task_planner_agent_tools()
    task_plan_critic_tools = create_task_plan_critic_agent_tools()
    task_critic_tools = create_task_critic_agent_tools()
    coder_tools = create_coder_agent_tools(coder_platform_tools, platform_type, tooling, stack=stack)
    code_reviewer_tools = create_code_reviewer_agent_tools(platform_type, stack=stack)
    automated_quality_checker_tools = create_automated_quality_checker_agent_tools(tooling, stack=stack)
    spec_alignment_reviewer_tools = create_spec_alignment_reviewer_agent_tools()
    frontend_reviewer_tools = create_frontend_reviewer_agent_tools()
    backend_api_reviewer_tools = create_backend_api_reviewer_agent_tools()
    database_reviewer_tools = create_database_reviewer_agent_tools()
    infrastructure_reviewer_tools = create_infrastructure_reviewer_agent_tools()
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
        ('respec-review-consolidator', generate_review_consolidator_template(review_consolidator_tools)),
    ]


def main() -> int:
    print("\n⚠️  WARNING: 'respec-setup' is deprecated.", file=sys.stderr)
    print("    Use 'respec-ai init' instead.", file=sys.stderr)
    print('    This command will be removed in v0.3.0\n', file=sys.stderr)

    parser = argparse.ArgumentParser(description='Set up respec-ai workflow files for a project')
    parser.add_argument('--project-path', required=True, help='Absolute path to project directory')
    parser.add_argument('--plan-name', required=True, help='Name for this project')
    parser.add_argument(
        '--platform',
        required=True,
        choices=['linear', 'github', 'markdown'],
        help='Platform type',
    )

    args = parser.parse_args()

    return setup_project(args.project_path, args.platform, args.plan_name)


if __name__ == '__main__':
    sys.exit(main())
