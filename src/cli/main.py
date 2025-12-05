#!/usr/bin/env python3
"""Main CLI entry point for respec-ai package.

Provides commands for:
- Project initialization (init)
- Platform switching (platform)
- Status checking (status)
- Validation (validate)
- Template upgrades (upgrade)
- MCP registration (register-mcp)
- Docker container management (docker)
"""

import sys
from argparse import ArgumentParser

from src.cli.config.package_info import get_package_version


from src.cli.commands import init
from src.cli.commands import platform
from src.cli.commands import status
from src.cli.commands import validate
from src.cli.commands import upgrade
from src.cli.commands import update
from src.cli.commands import register_mcp
from src.cli.commands import docker


def main() -> int:
    """Main entry point for respec-ai CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = ArgumentParser(
        prog='respec-ai',
        description='AI-powered specification workflow automation for Claude Code',
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'respec-ai {get_package_version()}',
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True,
    )

    init_parser = subparsers.add_parser(
        'init',
        help='Initialize RespecAI in current project',
    )

    init.add_arguments(init_parser)

    platform_parser = subparsers.add_parser(
        'platform',
        help='Change platform and regenerate templates',
    )

    platform.add_arguments(platform_parser)

    status_parser = subparsers.add_parser(
        'status',
        help='Show project configuration and status',
    )

    status.add_arguments(status_parser)

    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate project setup with diagnostics',
    )

    validate.add_arguments(validate_parser)

    upgrade_parser = subparsers.add_parser(
        'upgrade',
        help='Update templates to latest version',
    )

    upgrade.add_arguments(upgrade_parser)

    update_parser = subparsers.add_parser(
        'update',
        help='Update respec-ai CLI and Docker image to latest version',
    )

    update.add_arguments(update_parser)

    register_mcp_parser = subparsers.add_parser(
        'register-mcp',
        help='Register RespecAI MCP server in Claude Code',
    )

    register_mcp.add_arguments(register_mcp_parser)

    docker_parser = subparsers.add_parser(
        'docker',
        help='Manage Docker containers for MCP server',
    )

    docker.add_arguments(docker_parser)

    args = parser.parse_args()

    match args.command:
        case 'init':
            return init.run(args)
        case 'platform':
            return platform.run(args)
        case 'status':
            return status.run(args)
        case 'validate':
            return validate.run(args)
        case 'upgrade':
            return upgrade.run(args)
        case 'update':
            return update.run(args)
        case 'register-mcp':
            return register_mcp.run(args)
        case 'docker':
            return docker.run(args)
        case _:
            parser.print_help()
            return 1


if __name__ == '__main__':
    sys.exit(main())
