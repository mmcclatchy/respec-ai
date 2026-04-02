#!/usr/bin/env python3
"""Regenerate command and agent templates after terminology migration."""

from argparse import ArgumentParser
from pathlib import Path

from fastmcp import FastMCP

from src.mcp.tools import register_all_tools
from src.platform.platform_orchestrator import PlatformOrchestrator
from src.platform.platform_selector import PlatformType
from src.platform.template_generator import generate_templates
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_selector import TuiType


def main() -> None:
    parser = ArgumentParser(description='Regenerate respec-ai templates')
    parser.add_argument(
        '--tui',
        choices=[t.value for t in TuiType],
        default=TuiType.CLAUDE_CODE.value,
        help='Terminal UI target for generated templates',
    )
    args = parser.parse_args()

    project_path = Path.cwd()
    orchestrator = PlatformOrchestrator.create_with_default_config()
    platform_type = PlatformType.MARKDOWN
    tui_adapter = get_tui_adapter(TuiType(args.tui))

    print(f'Regenerating templates for: {project_path}')
    print(f'Platform type: {platform_type.value}')
    print(f'TUI target: {tui_adapter.display_name}')

    mcp = FastMCP('template-generator')
    register_all_tools(mcp)
    print('✓ Registered MCP tools for documentation extraction')

    files_written, commands_count, agents_count = generate_templates(
        orchestrator=orchestrator,
        project_path=project_path,
        platform_type=platform_type,
        mcp=mcp,
        tui_adapter=tui_adapter,
    )

    print('\n✅ Template generation complete!')
    print(f'Commands generated: {commands_count}')
    print(f'Agents generated: {agents_count}')
    print(f'Total files written: {len(files_written)}')
    print('\nFiles written:')
    for file_path in files_written:
        print(f'  - {file_path.relative_to(project_path)}')


if __name__ == '__main__':
    main()
