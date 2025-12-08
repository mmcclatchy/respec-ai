#!/usr/bin/env python3
"""Main CLI entry point for respec-ai package.

Provides commands for:
- Project initialization (init)
- Platform switching (platform)
- Status checking (status)
- Validation (validate)
- Template regeneration (regenerate)
- Project rebuild (rebuild)
- Package updates (update)
- MCP registration (register-mcp)
- MCP unregistration (unregister-mcp)
- Cleanup (cleanup)
- Docker container management (docker)
"""

import sys
from argparse import ArgumentParser

from src.cli.commands import (
    cleanup,
    docker,
    init,
    mcp_server,
    platform,
    rebuild,
    regenerate,
    register_mcp,
    status,
    unregister_mcp,
    update,
    validate,
)
from src.cli.config.package_info import get_package_version


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
        help='Initialize respec-ai in current project',
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

    regenerate_parser = subparsers.add_parser(
        'regenerate',
        help='Regenerate agent and command templates',
    )

    regenerate.add_arguments(regenerate_parser)

    rebuild_parser = subparsers.add_parser(
        'rebuild',
        help='Rebuild project configuration with current package version',
    )

    rebuild.add_arguments(rebuild_parser)

    update_parser = subparsers.add_parser(
        'update',
        help='Update respec-ai CLI and Docker image to latest version',
    )

    update.add_arguments(update_parser)

    register_mcp_parser = subparsers.add_parser(
        'register-mcp',
        help='Register respec-ai MCP server in Claude Code',
    )

    register_mcp.add_arguments(register_mcp_parser)

    unregister_mcp_parser = subparsers.add_parser(
        'unregister-mcp',
        help='Unregister respec-ai MCP server from Claude Code',
    )

    unregister_mcp.add_arguments(unregister_mcp_parser)

    cleanup_parser = subparsers.add_parser(
        'cleanup',
        help='Clean up all respec-ai installations and configurations',
    )

    cleanup.add_arguments(cleanup_parser)

    docker_parser = subparsers.add_parser(
        'docker',
        help='Manage Docker containers for MCP server',
    )

    docker.add_arguments(docker_parser)

    mcp_server_parser = subparsers.add_parser(
        'mcp-server',
        help='Start respec-ai MCP server (used by Claude Code)',
    )

    mcp_server.add_arguments(mcp_server_parser)

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
        case 'regenerate':
            return regenerate.run(args)
        case 'rebuild':
            return rebuild.run(args)
        case 'update':
            return update.run(args)
        case 'register-mcp':
            return register_mcp.run(args)
        case 'unregister-mcp':
            return unregister_mcp.run(args)
        case 'cleanup':
            return cleanup.run(args)
        case 'docker':
            return docker.run(args)
        case 'mcp-server':
            return mcp_server.run(args)
        case _:
            parser.print_help()
            return 1


if __name__ == '__main__':
    sys.exit(main())
