import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from src.cli.config.claude_config import ClaudeConfigError
from src.cli.config.package_info import get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import print_error, print_info, print_success, print_warning
from src.platform.tui_adapters import get_tui_adapter
from src.platform.tui_selector import TuiType


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help='Re-register even if already registered',
    )


def run(args: Namespace) -> int:
    try:
        project_path = Path.cwd().resolve()
        config_path = project_path / '.respec-ai' / 'config.json'

        if not config_path.exists():
            print_error('respec-ai is not initialized in this project')
            print_warning('Run: respec-ai init --platform [linear|github|markdown]')
            return 1

        config = json.loads(config_path.read_text(encoding='utf-8'))
        tui = config.get('tui', 'claude-code')
        tui_adapter = get_tui_adapter(TuiType(tui))

        if tui_adapter.is_mcp_registered(project_path) and not args.force:
            print_info('respec-ai MCP server is already registered')
            print_info('Use --force to re-register')
            return 0

        docker_manager = DockerManager()
        version = get_package_version()
        container_status = docker_manager.get_container_status()

        if not container_status['exists']:
            print_warning(f"Docker container 'respec-ai-{version}' does not exist")
            print_info('Run: respec-ai docker pull')
            return 1

        if not container_status['running']:
            print_warning(f"Docker container 'respec-ai-{version}' is not running")
            print_info('Starting container...')
            docker_manager.ensure_running()
            print_success('Container started successfully')

        registered = tui_adapter.register_mcp_server(project_path)

        if registered:
            if args.force:
                print_success('respec-ai MCP server re-registered successfully')
            else:
                print_success('respec-ai MCP server registered successfully')

            print_info(f'Container: respec-ai-{version}')
            print_info('Communication: stdio via docker exec')
            tui_label = 'OpenCode' if tui == 'opencode' else 'Claude Code'
            print_info(f'Restart {tui_label} to activate the MCP server')
        else:
            print_info('respec-ai MCP server is already registered')

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
    parser = ArgumentParser(description='Register respec-ai MCP server')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
