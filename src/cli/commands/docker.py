import sys
from argparse import ArgumentParser, Namespace

from rich.table import Table
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_success, print_warning


def add_arguments(parser: ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest='docker_command', required=True, help='Docker commands')

    subparsers.add_parser('status', help='Show container status')

    subparsers.add_parser('start', help='Start container (auto-cleanup old versions)')

    stop_parser = subparsers.add_parser('stop', help='Stop container gracefully')
    stop_parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Shutdown timeout in seconds (default: 10)',
    )

    subparsers.add_parser('restart', help='Restart container')

    logs_parser = subparsers.add_parser('logs', help='Show container logs')
    logs_parser.add_argument(
        '--lines',
        type=int,
        default=100,
        help='Number of log lines to show (default: 100)',
    )

    subparsers.add_parser('pull', help='Pull Docker image from registry (auto-cleanup old versions)')

    subparsers.add_parser('cleanup', help='Remove all old containers and images (manual cleanup)')


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
        elif args.docker_command == 'cleanup':
            return _run_cleanup(manager, args)
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
    status = manager.get_container_status()

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

    return 0


def _run_start(manager: DockerManager, args: Namespace) -> int:
    manager.cleanup_old_versions()
    manager.start_container()
    print_success('Container started successfully')
    return 0


def _run_stop(manager: DockerManager, args: Namespace) -> int:
    timeout = args.timeout
    manager.stop_container(None, timeout)
    print_success('Container stopped successfully')
    return 0


def _run_restart(manager: DockerManager, args: Namespace) -> int:
    manager.restart_container()
    print_success('Container restarted successfully')
    return 0


def _run_logs(manager: DockerManager, args: Namespace) -> int:
    lines = args.lines
    logs = manager.get_container_logs(None, lines)
    console.print()
    console.print(logs)
    console.print()
    return 0


def _run_pull(manager: DockerManager, args: Namespace) -> int:
    manager.cleanup_old_versions()
    manager.pull_image()
    print_success('Image pulled successfully')
    return 0


def _run_cleanup(manager: DockerManager, args: Namespace) -> int:
    removed = manager.cleanup_old_versions()
    if removed:
        print_success(f'Cleaned up {removed} old version(s)')
    else:
        print_warning('No old versions to clean up')
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description='Manage RespecAI Docker containers')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
