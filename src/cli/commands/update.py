import subprocess
import sys
from argparse import ArgumentParser, Namespace

from src.cli.config.package_info import get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import print_error, print_info, print_success, print_warning


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--index-url',
        default='https://test.pypi.org/simple/',
        help='PyPI index URL to check (default: TestPyPI)',
    )
    parser.add_argument(
        '--extra-index-url',
        default='https://pypi.org/simple/',
        help='Additional index URL for dependencies (default: PyPI)',
    )
    parser.add_argument(
        '--skip-docker',
        action='store_true',
        help='Skip Docker image update',
    )


def run(args: Namespace) -> int:
    """Update respec-ai CLI and Docker image to latest version.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        current_version = get_package_version()
        print_info(f'Current version: {current_version}')
        print_info('Checking for updates...')

        # Update CLI package
        result = subprocess.run(
            [
                'uv',
                'tool',
                'upgrade',
                '--index-url',
                args.index_url,
                '--extra-index-url',
                args.extra_index_url,
                'respec-ai',
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print_error('Failed to update CLI package')
            print_error(result.stderr)
            return 1

        # Check if version changed
        new_version = get_package_version()
        if new_version == current_version:
            print_info(f'Already on latest version: {current_version}')
            if not args.skip_docker:
                print_info('Checking Docker image...')
        else:
            print_success(f'Updated CLI: {current_version} → {new_version}')

        # Update Docker image
        if not args.skip_docker:
            try:
                docker_manager = DockerManager()

                # Stop old container if running
                old_status = docker_manager.get_container_status()
                was_running = old_status.get('running', False)

                if was_running:
                    print_info('Stopping old container...')
                    docker_manager.stop_container()

                # Pull new image (auto-cleans old versions)
                print_info('Pulling Docker image...')
                docker_manager.cleanup_old_versions()
                docker_manager.pull_image()
                print_success('Docker image updated')

                # Start new container if old one was running
                if was_running:
                    print_info('Starting new container...')
                    docker_manager.start_container()
                    print_success('Container started')

            except DockerManagerError as e:
                print_warning('Docker update failed (CLI update succeeded)')
                print_error(str(e))
                print_info('You can manually update Docker with: respec-ai docker pull')
                return 1

        print_success('Update complete!')
        if new_version != current_version:
            print_info(f'New version: {new_version}')
            print_info('Run `respec-ai --version` to confirm')

        return 0

    except Exception as e:
        print_error(f'Update failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Update respec-ai to latest version')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
