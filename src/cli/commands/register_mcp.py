import sys
from argparse import ArgumentParser, Namespace

from src.cli.config.claude_config import (
    ClaudeConfigError,
    get_mcp_server_config,
    register_mcp_server,
)
from src.cli.config.package_info import get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import print_error, print_info, print_success, print_warning


def add_arguments(parser: ArgumentParser) -> None:
    """Add command-specific arguments.

    Args:
        parser: Argument parser for this command
    """
    parser.add_argument(
        '--force',
        action='store_true',
        help='Re-register even if already registered',
    )


def run(args: Namespace) -> int:
    """Register RespecAI MCP server in Claude Code configuration.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        existing_config = get_mcp_server_config()

        if existing_config and not args.force:
            print_info('RespecAI MCP server is already registered')
            print_info('Use --force to re-register')
            return 0

        docker_manager = DockerManager()
        version = get_package_version()
        container_status = docker_manager.get_container_status()

        if not container_status['exists']:
            print_warning(f"Docker container 'respec-ai-{version}' does not exist")
            print_info('Run: respec-ai docker pull')
            print_info('Or: respec-ai docker build')
            return 1

        if not container_status['running']:
            print_warning(f"Docker container 'respec-ai-{version}' is not running")
            print_info('Starting container...')
            docker_manager.ensure_running()
            print_success('Container started successfully')

        registered = register_mcp_server(force=args.force)

        if registered:
            if args.force:
                print_success('RespecAI MCP server re-registered successfully')
            else:
                print_success('RespecAI MCP server registered successfully')

            print_info(f'Container: respec-ai-{version}')
            print_info('Communication: stdio via docker exec')
            print_info('Restart Claude Code to activate the MCP server')
        else:
            print_info('RespecAI MCP server is already registered')

        return 0

    except DockerManagerError as e:
        print_error('Docker error:')
        print_error(str(e))
        print_info('Ensure Docker is installed and running')
        return 1

    except ClaudeConfigError as e:
        print_error('Failed to register MCP server')
        print_error(str(e))
        return 1

    except Exception as e:
        print_error(f'Unexpected error: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Register RespecAI MCP server')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
