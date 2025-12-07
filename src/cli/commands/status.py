import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.claude_config import is_mcp_server_registered
from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.cli.config.package_info import get_package_version
from src.cli.ui.console import console, print_error, print_warning
from src.cli.ui.formatters import format_file_counts_table, format_project_config_table


def add_arguments(parser: ArgumentParser) -> None:
    """Add command-specific arguments.

    Args:
        parser: Argument parser for this command
    """
    pass


def run(args: Namespace) -> int:
    """Show RespecAI project status and configuration.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'

        if not config_path.exists():
            print_error('RespecAI is not initialized in this project')
            print_warning('Run: respec-ai init --platform [linear|github|markdown]')
            return 1

        config = json.loads(config_path.read_text(encoding='utf-8'))

        platform = config.get('platform', 'unknown')
        version = config.get('version', 'unknown')
        package_version = get_package_version()

        mcp_registered = is_mcp_server_registered()

        commands_dir = get_commands_dir(project_path)
        agents_dir = get_agents_dir(project_path)

        commands_count = len(list(commands_dir.glob('*.md'))) if commands_dir.exists() else 0
        agents_count = len(list(agents_dir.glob('*.md'))) if agents_dir.exists() else 0

        console.print()
        config_table = format_project_config_table(
            project_path=project_path,
            platform=platform,
            version=version,
            package_version=package_version,
            mcp_registered=mcp_registered,
        )
        console.print(config_table)

        console.print()
        files_table = format_file_counts_table(
            commands_count=commands_count,
            agents_count=agents_count,
        )
        console.print(files_table)

        console.print()

        if not mcp_registered:
            print_warning('MCP server not registered')
            print_warning('Run: respec-ai register-mcp')
            console.print()

        if version != package_version:
            print_warning(f'Config version ({version}) != package version ({package_version})')
            print_warning('Run: respec-ai regenerate')
            console.print()

        return 0

    except json.JSONDecodeError as e:
        print_error(f'Config file is corrupted: {e}')
        print_warning('Delete .respec-ai/config.json and run: respec-ai init')
        return 1

    except Exception as e:
        print_error(f'Status check failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Show RespecAI project status')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
