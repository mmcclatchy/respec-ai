#!/usr/bin/env python3
"""CLI for setting up Specter in projects.

This CLI is called by install-specter.sh to generate platform-specific
workflow files directly, eliminating the need for the /init-specter command.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

from services.platform.models import (
    BuildCoderAgentTools,
    CreateSpecAgentTools,
    PlanRoadmapAgentTools,
)
from services.platform.platform_orchestrator import PlatformOrchestrator
from services.platform.platform_selector import PlatformType
from services.platform.tool_enums import AbstractOperation, CommandTemplate
from services.platform.tool_registry import ToolRegistry
from services.templates.agents.analyst_critic import generate_analyst_critic_template
from services.templates.agents.build_coder import generate_build_coder_template
from services.templates.agents.build_critic import generate_build_critic_template
from services.templates.agents.build_planner import generate_build_planner_template
from services.templates.agents.build_reviewer import generate_build_reviewer_template
from services.templates.agents.create_spec import generate_create_spec_template
from services.templates.agents.plan_analyst import generate_plan_analyst_template
from services.templates.agents.plan_critic import generate_plan_critic_template
from services.templates.agents.roadmap import generate_roadmap_template
from services.templates.agents.roadmap_critic import generate_roadmap_critic_template


def setup_project(project_path: str, platform: Literal['linear', 'github', 'markdown']) -> int:
    """Set up Specter workflow files for a project.

    Args:
        project_path: Absolute path to project directory
        platform: Platform type (linear, github, or markdown)

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
        (project / '.specter').mkdir(parents=True, exist_ok=True)

        files_written: list[str] = []

        command_templates = [
            CommandTemplate.PLAN,
            CommandTemplate.SPEC,
            CommandTemplate.BUILD,
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

        config = {'platform': platform, 'created_at': datetime.now().isoformat(), 'version': '1.0'}
        config_path = project / '.specter' / 'config.json'
        config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        files_written.append(str(config_path.relative_to(project)))

        print('✅ Specter setup complete!')
        print(f'\nPlatform: {platform}')
        print(f'Files Created: {len(files_written)}')
        print(f'Location: {project}')
        print('\n⚠️  IMPORTANT: Restart Claude Code to activate the new commands!')
        print('\nAvailable Commands (after restart):')
        print('  • /specter-plan - Create strategic plans')
        print('  • /specter-spec - Transform plans into technical specifications')
        print('  • /specter-build - Execute implementation workflows')
        print('  • /specter-roadmap - Create phased roadmaps')
        print('  • /specter-plan-conversation - Convert conversations into plans')
        print('\n🚀 Ready to begin! Restart Claude Code to use the Specter commands.')

        return 0

    except ValueError:
        print(f'❌ Error: Invalid platform "{platform}". Must be: linear, github, or markdown', file=sys.stderr)
        return 1
    except Exception as e:
        print(f'❌ Error: Setup failed: {e}', file=sys.stderr)
        return 1


def _get_agent_generators(orchestrator: PlatformOrchestrator, platform_type: PlatformType) -> list[tuple[str, str]]:
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

    return [
        ('specter-plan-analyst', generate_plan_analyst_template()),
        ('specter-plan-critic', generate_plan_critic_template()),
        ('specter-analyst-critic', generate_analyst_critic_template()),
        ('specter-roadmap', generate_roadmap_template(roadmap_tools)),
        ('specter-roadmap-critic', generate_roadmap_critic_template()),
        ('specter-create-spec', generate_create_spec_template(spec_tools)),
        ('specter-build-planner', generate_build_planner_template()),
        ('specter-build-critic', generate_build_critic_template()),
        ('specter-build-coder', generate_build_coder_template(build_coder_tools)),
        ('specter-build-reviewer', generate_build_reviewer_template()),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description='Set up Specter workflow files for a project')
    parser.add_argument('--project-path', required=True, help='Absolute path to project directory')
    parser.add_argument(
        '--platform',
        required=True,
        choices=['linear', 'github', 'markdown'],
        help='Platform type',
    )

    args = parser.parse_args()

    return setup_project(args.project_path, args.platform)


if __name__ == '__main__':
    sys.exit(main())
