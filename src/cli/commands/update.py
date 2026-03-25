import subprocess
import sys
from argparse import ArgumentParser, Namespace

from src.cli.config.package_info import get_package_version
from src.cli.docker.manager import DockerManager, DockerManagerError
from src.cli.ui.console import print_error, print_info, print_success, print_warning


GITHUB_REPO_URL = 'git+https://github.com/mmcclatchy/respec-ai.git'


def add_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--skip-docker',
        action='store_true',
        help='Skip Docker image update',
    )


def _update_docker(new_version: str) -> bool:
    try:
        docker_manager = DockerManager()
    except DockerManagerError as e:
        print_warning(f'Docker not available: {e}')
        print_info('Skip Docker update with: respec-ai update --skip-docker')
        return False

    old_status = docker_manager.get_container_status()
    was_running = old_status.get('running', False)

    if was_running:
        print_info('Stopping container...')
        docker_manager.stop_container()

    print_info(f'Pulling Docker image v{new_version}...')
    try:
        docker_manager.pull_image(version=new_version)
        print_success('Docker image updated')
    except DockerManagerError:
        print_warning(f'Docker image v{new_version} not yet available on registry')
        print_info('The GitHub Actions build may still be in progress')
        print_info('To pull manually once ready: respec-ai docker pull')

        if was_running:
            print_info('Restarting previous container...')
            try:
                docker_manager.ensure_running()
                print_success('Previous container restored')
            except DockerManagerError:
                print_warning('Could not restart previous container')
                print_info('Start manually when image is ready: respec-ai docker start')
        return False

    docker_manager.cleanup_old_versions(version=new_version)

    print_info('Starting container...')
    try:
        docker_manager.start_container(version=new_version)
        print_success('Container running')
    except DockerManagerError as e:
        print_warning(f'Failed to start container: {e}')
        print_info('Start manually: respec-ai docker start')
        return False

    return True


def run(args: Namespace) -> int:
    try:
        current_version = get_package_version()
        print_info(f'Current version: {current_version}')
        print_info('Checking for updates...')

        result = subprocess.run(
            ['uv', 'tool', 'install', '--force', GITHUB_REPO_URL],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print_error('Failed to update CLI package')
            print_error(result.stderr)
            return 1

        new_version = get_package_version()

        if new_version == current_version:
            print_info(f'Already on latest version: {current_version}')
        else:
            print_success(f'Updated CLI: {current_version} → {new_version}')

        if not args.skip_docker:
            _update_docker(new_version)

        print_success('Update complete!')
        if new_version != current_version:
            print_info(f'New version: {new_version}')

        return 0

    except Exception as e:
        print_error(f'Update failed: {e}')
        return 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Update respec-ai to latest version')
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run(args))
