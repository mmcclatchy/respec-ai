import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.claude_config import is_mcp_server_registered
from src.cli.config.ide_constants import get_agents_dir, get_commands_dir
from src.cli.config.package_info import get_package_version
from src.cli.ui.formatters import print_validation_report


def add_arguments(parser: ArgumentParser) -> None:
    """Add command-specific arguments.

    Args:
        parser: Argument parser for this command
    """
    pass


def run(args: Namespace) -> int:
    """Validate respec-ai project configuration and setup.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 if all checks pass, 1 if any check fails)
    """
    project_path = Path.cwd().resolve()
    checks: dict[str, tuple[bool, str]] = {}

    config_path = project_path / '.respec-ai' / 'config.json'
    if config_path.exists():
        checks['Project Initialized'] = (True, 'Config file exists')

        try:
            config = json.loads(config_path.read_text(encoding='utf-8'))
            checks['Config Valid'] = (True, 'Config is valid JSON')

            platform = config.get('platform')
            if platform in ['linear', 'github', 'markdown']:
                checks['Platform Valid'] = (True, f'Platform: {platform}')
            else:
                checks['Platform Valid'] = (False, f'Invalid platform: {platform}')

            version = config.get('version', 'unknown')
            package_version = get_package_version()
            if version == package_version:
                checks['Version Current'] = (True, f'Version: {version}')
            else:
                checks['Version Current'] = (False, f'{version} != {package_version} (upgrade needed)')

        except json.JSONDecodeError as e:
            checks['Config Valid'] = (False, f'JSON error: {e}')
            checks['Platform Valid'] = (False, 'Cannot read platform')
            checks['Version Current'] = (False, 'Cannot read version')

    else:
        checks['Project Initialized'] = (False, 'Not initialized')
        checks['Config Valid'] = (False, 'Config missing')
        checks['Platform Valid'] = (False, 'Config missing')
        checks['Version Current'] = (False, 'Config missing')

    commands_dir = get_commands_dir(project_path)
    if commands_dir.exists():
        commands_count = len(list(commands_dir.glob('*.md')))
        if commands_count == 5:
            checks['Commands Directory'] = (True, f'{commands_count} commands found')
        else:
            checks['Commands Directory'] = (False, f'{commands_count} commands (expected 5)')
    else:
        checks['Commands Directory'] = (False, 'Directory missing')

    agents_dir = get_agents_dir(project_path)
    if agents_dir.exists():
        agents_count = len(list(agents_dir.glob('*.md')))
        if agents_count == 12:
            checks['Agents Directory'] = (True, f'{agents_count} agents found')
        else:
            checks['Agents Directory'] = (False, f'{agents_count} agents (expected 12)')
    else:
        checks['Agents Directory'] = (False, 'Directory missing')

    mcp_registered = is_mcp_server_registered()
    if mcp_registered:
        checks['MCP Registered'] = (True, 'respec-ai server registered')
    else:
        checks['MCP Registered'] = (False, 'Not registered in Claude Code')

    all_passed = all(passed for passed, _ in checks.values())

    print_validation_report(
        project_path=project_path,
        checks=checks,
        all_passed=all_passed,
    )

    if not all_passed:
        return 1

    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description='Validate respec-ai project setup')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
