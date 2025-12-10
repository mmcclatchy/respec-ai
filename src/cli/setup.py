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
from typing import Literal

from src.platform.models import (
    CreatePhaseAgentTools,
    PhaseArchitectAgentTools,
    PhaseCriticAgentTools,
    PlanRoadmapAgentTools,
    TaskCoderAgentTools,
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


def setup_project(project_path: str, platform: Literal['linear', 'github', 'markdown'], project_name: str) -> int:
    """Set up respec-ai workflow files for a project.

    Args:
        project_path: Absolute path to project directory
        platform: Platform type (linear, github, or markdown)
        project_name: Name for this project

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        project = Path(project_path).resolve()

        if not project.exists():
            print(f'❌ Error: Project directory does not exist: {project}', file=sys.stderr)
            return 1

        platform_type = PlatformType(platform)
        orchestrator = PlatformOrchestrator.create_with_default_config()

        (project / '.claude' / 'commands').mkdir(parents=True, exist_ok=True)
        (project / '.claude' / 'agents').mkdir(parents=True, exist_ok=True)
        (project / '.respec-ai').mkdir(parents=True, exist_ok=True)

        files_written: list[str] = []

        command_templates = [
            CommandTemplate.PLAN,
            CommandTemplate.PHASE,
            CommandTemplate.CODE,
            CommandTemplate.ROADMAP,
            CommandTemplate.PLAN_CONVERSATION,
        ]

        for cmd in command_templates:
            content = orchestrator.template_coordinator.generate_command_template(cmd, platform_type)
            file_path = project / '.claude' / 'commands' / f'{cmd.value}.md'
            file_path.write_text(content, encoding='utf-8')
            files_written.append(str(file_path.relative_to(project)))

        agent_generators = _get_agent_generators(orchestrator, platform_type)

        for agent_name, content in agent_generators:
            file_path = project / '.claude' / 'agents' / f'{agent_name}.md'
            file_path.write_text(content, encoding='utf-8')
            files_written.append(str(file_path.relative_to(project)))

        config = {
            'project_name': project_name,
            'platform': platform,
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
        }
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
        print('  • /respec-spec - Transform plans into technical specifications')
        print('  • /respec-build - Execute implementation workflows')
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


def _get_agent_generators(orchestrator: PlatformOrchestrator, platform_type: PlatformType) -> list[tuple[str, str]]:
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

    task_coder_tools = TaskCoderAgentTools(
        update_task_status=tool_registry.get_tool_for_platform(AbstractOperation.UPDATE_SPEC_TOOL.value, platform_type)
    )

    phase_architect_tools = PhaseArchitectAgentTools(tools_yaml=create_phase_architect_agent_tools())
    phase_critic_tools = PhaseCriticAgentTools(
        tools_yaml=create_phase_critic_agent_tools(), phase_length_soft_cap=loop_config.phase_length_soft_cap
    )

    return [
        ('respec-plan-analyst', generate_plan_analyst_template()),
        ('respec-plan-critic', generate_plan_critic_template()),
        ('respec-analyst-critic', generate_analyst_critic_template()),
        ('respec-roadmap', generate_roadmap_template(roadmap_tools)),
        ('respec-roadmap-critic', generate_roadmap_critic_template()),
        ('respec-create-phase', generate_create_phase_template(phase_tools)),
        ('respec-spec-architect', generate_phase_architect_template(phase_architect_tools)),
        ('respec-spec-critic', generate_phase_critic_template(phase_critic_tools)),
        ('respec-build-planner', generate_task_critic_template()),
        ('respec-build-critic', generate_task_critic_template()),
        ('respec-build-coder', generate_task_coder_template(task_coder_tools)),
        ('respec-build-reviewer', generate_task_reviewer_template()),
    ]


def main() -> int:
    print("\n⚠️  WARNING: 'respec-setup' is deprecated.", file=sys.stderr)
    print("    Use 'respec-ai init' instead.", file=sys.stderr)
    print('    This command will be removed in v0.3.0\n', file=sys.stderr)

    parser = argparse.ArgumentParser(description='Set up respec-ai workflow files for a project')
    parser.add_argument('--project-path', required=True, help='Absolute path to project directory')
    parser.add_argument('--project-name', required=True, help='Name for this project')
    parser.add_argument(
        '--platform',
        required=True,
        choices=['linear', 'github', 'markdown'],
        help='Platform type',
    )

    args = parser.parse_args()

    return setup_project(args.project_path, args.platform, args.project_name)


if __name__ == '__main__':
    sys.exit(main())
