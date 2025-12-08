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
