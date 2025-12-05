import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from rich.table import Table
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_success, print_warning


def add_arguments(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='docker_command', required=True, help='Docker commands')

    status_parser = subparsers.add_parser('status', help='Show container status')
    status_parser.add_argument(
        '--version',
        help='Specific version to check (defaults to CLI version)',
    )

    start_parser = subparsers.add_parser('start', help='Start container')
    start_parser.add_argument(
        '--version',
        help='Specific version to start (defaults to CLI version)',
    )

    stop_parser = subparsers.add_parser('stop', help='Stop container gracefully')
    stop_parser.add_argument(
        '--version',
        help='Specific version to stop (defaults to CLI version)',
    )
    stop_parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Shutdown timeout in seconds (default: 10)',
    )

    restart_parser = subparsers.add_parser('restart', help='Restart container')
    restart_parser.add_argument(
        '--version',
        help='Specific version to restart (defaults to CLI version)',
    )

    logs_parser = subparsers.add_parser('logs', help='Show container logs')
    logs_parser.add_argument(
        '--version',
        help='Specific version (defaults to CLI version)',
    )
    logs_parser.add_argument(
        '--lines',
        type=int,
        default=100,
        help='Number of log lines to show (default: 100)',
    )

    pull_parser = subparsers.add_parser('pull', help='Pull Docker image from registry')
    pull_parser.add_argument(
        '--version',
        help='Specific version to pull (defaults to CLI version)',
    )

    build_parser = subparsers.add_parser('build', help='Build Docker image from source')
    build_parser.add_argument(
        '--version',
        help='Specific version tag (defaults to CLI version)',
    )
    build_parser.add_argument(
        '--path',
        type=Path,
        default=Path.cwd(),
        help='Path to build context (default: current directory)',
    )

    subparsers.add_parser('list', help='List all respec-ai containers')


def run(args: Namespace) -> int:
    try:
        manager = DockerManager()

        if args.docker_command == 'status':
            return _run_status(manager, args)
        elif args.docker_command == 'start':
            return _run_start(manager, args)
        elif args.docker_command == 'stop':
            return _run_stop(manager, args)
        elif args.docker_command == 'restart':
            return _run_restart(manager, args)
        elif args.docker_command == 'logs':
            return _run_logs(manager, args)
        elif args.docker_command == 'pull':
            return _run_pull(manager, args)
        elif args.docker_command == 'build':
            return _run_build(manager, args)
        elif args.docker_command == 'list':
            return _run_list(manager, args)
        else:
            print_error(f'Unknown docker command: {args.docker_command}')
            return 1

    except DockerManagerError as e:
        print_error(f'Docker error: {e}')
        return 1
    except Exception as e:
        print_error(f'Command failed: {e}')
        return 1


def _run_status(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    status = manager.get_container_status(version)

    table = Table(title='Container Status')
    table.add_column('Property', style='cyan')
    table.add_column('Value', style='green')

    table.add_row('Container Name', status['name'])
    table.add_row('Exists', '✓ Yes' if status['exists'] else '✗ No')
    table.add_row('Running', '✓ Yes' if status['running'] else '✗ No')
    table.add_row('Status', status['status'])

    if status['exists']:
        table.add_row('ID', status.get('id', 'unknown'))
        table.add_row('Image', status.get('image', 'unknown'))
        table.add_row('Created', status.get('created', 'unknown'))

    console.print()
    console.print(table)
    console.print()

    if not status['exists']:
        print_warning(f'Container {status["name"]} does not exist')
        print_warning('Run: respec-ai docker pull')
        print_warning('Or: respec-ai docker build')

    return 0


def _run_start(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    manager.start_container(version)
    print_success('Container started successfully')
    return 0


def _run_stop(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    timeout = args.timeout
    manager.stop_container(version, timeout)
    print_success('Container stopped successfully')
    return 0


def _run_restart(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    manager.restart_container(version)
    print_success('Container restarted successfully')
    return 0


def _run_logs(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    lines = args.lines
    logs = manager.get_container_logs(version, lines)
    console.print()
    console.print(logs)
    console.print()
    return 0


def _run_pull(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    manager.pull_image(version)
    print_success('Image pulled successfully')
    return 0


def _run_build(manager: DockerManager, args: Namespace) -> int:
    version = args.version
    path = args.path
    manager.build_image(version, path)
    print_success('Image built successfully')
    return 0


def _run_list(manager: DockerManager, args: Namespace) -> int:
    containers = manager.list_all_containers()

    if not containers:
        print_warning('No respec-ai containers found')
        return 0

    table = Table(title='RespecAI Containers')
    table.add_column('Name', style='cyan')
    table.add_column('Status', style='green')
    table.add_column('Image', style='yellow')
    table.add_column('ID', style='blue')

    for container in containers:
        table.add_row(
            container['name'],
            container['status'],
            container['image'],
            container['id'],
        )

    console.print()
    console.print(table)
    console.print()
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description='Manage RespecAI Docker containers')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
