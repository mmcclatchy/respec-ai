import subprocess
import sys
from argparse import ArgumentParser, Namespace

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import console, print_error, print_info, print_success, print_warning


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
        '-n',
        '--lines',
        type=int,
        default=100,
        help='Number of log lines to show (default: 100)',
    )

    subparsers.add_parser('pull', help='Pull Docker image from registry (auto-cleanup old versions)')

    cleanup_parser = subparsers.add_parser('cleanup', help='Remove old versions or dangling images')
    cleanup_parser.add_argument(
        '-d',
        '--dangling',
        action='store_true',
        help='Remove dangling (untagged) images instead of old versions',
    )

    remove_parser = subparsers.add_parser('remove', help='Remove prod containers, image, and network')
    remove_parser.add_argument('-f', '--force', action='store_true', help='Force stop containers if hanging')
    remove_parser.add_argument(
        '--volumes',
        action='store_true',
        help='Also remove database volume (WARNING: deletes all data)',
    )

    subparsers.add_parser('list', help='Show respec-ai prod containers only')

    subparsers.add_parser('bash', help='Enter bash shell in server container')

    exec_parser = subparsers.add_parser('exec', help='Execute command in server container')
    exec_parser.add_argument('command', help='Command to execute in container')


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
        elif args.docker_command == 'remove':
            return _run_remove(manager, args)
        elif args.docker_command == 'list':
            return _run_list(manager, args)
        elif args.docker_command == 'bash':
            return _run_bash(manager, args)
        elif args.docker_command == 'exec':
            return _run_exec(manager, args)
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

    if not logs or logs.strip() == '':
        console.print()
        console.print('[yellow]No logs available[/yellow]')
        console.print('[dim]Container may not have started any processes yet[/dim]')
        console.print('[dim]MCP server starts only when Claude Code connects[/dim]')
        console.print()
        console.print('[cyan]To verify container is running:[/cyan]')
        console.print('  respec-ai status')
        console.print()
        return 0

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
    if args.dangling:
        return _run_cleanup_dangling(manager, args)

    removed = manager.cleanup_old_versions()
    if removed:
        print_success(f'Cleaned up {removed} old version(s)')
    else:
        print_warning('No old versions to clean up')
    return 0


def _run_cleanup_dangling(manager: DockerManager, args: Namespace) -> int:
    console.print()
    console.print('[yellow]WARNING: This will remove ALL dangling images system-wide[/yellow]')
    console.print('[dim]Dangling images are untagged images from failed builds/pulls[/dim]')
    console.print('[dim]This affects all Docker projects, not just respec-ai[/dim]')
    console.print()

    response = input('Continue? [y/N]: ')
    if response.lower() != 'y':
        print_warning('Cleanup cancelled')
        return 0

    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description}'),
            console=console,
        ) as progress:
            task = progress.add_task('Removing dangling images...', total=None)

            images_removed, space_reclaimed = manager.cleanup_dangling_images()

            progress.update(task, description='Complete!', completed=True)

        console.print()

        if images_removed > 0:
            space_mb = space_reclaimed / (1024 * 1024)
            print_success(f'Removed {images_removed} dangling image(s)')
            print_success(f'Reclaimed {space_mb:.2f} MB of disk space')
        else:
            print_info('No dangling images to clean up')

        console.print()
        return 0

    except DockerManagerError as e:
        print_error(f'Cleanup failed: {e}')
        return 1


def _run_remove(manager: DockerManager, args: Namespace) -> int:
    force = args.force
    remove_volumes = args.volumes

    if remove_volumes:
        console.print('[yellow]WARNING: --volumes will delete all database data[/yellow]')
        console.print('[yellow]This cannot be undone![/yellow]')
        response = input('Type "yes" to confirm: ')
        if response.lower() != 'yes':
            print_warning('Aborted')
            return 0

    with Progress(
        SpinnerColumn(),
        TextColumn('[progress.description]{task.description}'),
        console=console,
    ) as progress:
        task = progress.add_task('Removing containers...', total=None)

        progress.update(task, description='Removing server container...')
        try:
            manager.remove_container(force=force)
        except DockerManagerError:
            pass

        progress.update(task, description='Removing database container...')
        try:
            manager.remove_database_container(force=force)
        except DockerManagerError:
            pass

        progress.update(task, description='Removing image...')
        try:
            manager.remove_image()
        except DockerManagerError:
            pass

        progress.update(task, description='Removing network...')
        try:
            manager.remove_network()
        except DockerManagerError:
            pass

        if remove_volumes:
            progress.update(task, description='Removing volume...')
            try:
                manager.remove_volume()
            except DockerManagerError:
                pass

        progress.update(task, description='Complete!', completed=True)

    console.print()
    print_success('Prod containers removed successfully')
    if not remove_volumes:
        print_info('Database volume preserved (use --volumes to remove)')
    console.print()

    return 0


def _run_list(manager: DockerManager, args: Namespace) -> int:
    containers = manager.list_prod_containers()

    table = Table(title='respec-ai Prod Containers')
    table.add_column('Name', style='cyan')
    table.add_column('Status', style='green')
    table.add_column('Image', style='blue')
    table.add_column('Created', style='dim')

    for container in containers:
        status = '✓ Running' if container['running'] else '✗ Stopped'
        table.add_row(container['name'], status, container['image'], container['created'])

    console.print()
    console.print(table)
    console.print()

    if not containers:
        print_warning('No prod containers found')
        print_info('Run: respec-ai docker pull')

    return 0


def _run_bash(manager: DockerManager, args: Namespace) -> int:
    status = manager.get_container_status()

    if not status['running']:
        print_error('Server container is not running')
        print_info('Run: respec-ai docker start')
        return 1

    console.print('[cyan]Entering bash shell in server container...[/cyan]')
    console.print('[dim]Type "exit" to return[/dim]')
    console.print()

    result = subprocess.run(['docker', 'exec', '-it', status['name'], 'bash'], check=False)
    return result.returncode


def _run_exec(manager: DockerManager, args: Namespace) -> int:
    status = manager.get_container_status()

    if not status['running']:
        print_error('Server container is not running')
        print_info('Run: respec-ai docker start')
        return 1

    result = subprocess.run(['docker', 'exec', '-it', status['name'], 'bash', '-c', args.command], check=False)
    return result.returncode


if __name__ == '__main__':
    parser = ArgumentParser(description='Manage respec-ai Docker containers')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
