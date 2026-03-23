import re
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


def _parse_installed_version(uv_output: str) -> str | None:
    match = re.search(r'respec-ai==([^\s(]+)', uv_output)
    return match.group(1) if match else None


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

        combined_output = result.stdout + result.stderr
        new_version = _parse_installed_version(combined_output) or current_version

        if new_version == current_version:
            print_info(f'Already on latest version: {current_version}')
            if not args.skip_docker:
                print_info('Checking Docker image...')
        else:
            print_success(f'Updated CLI: {current_version} → {new_version}')

        if not args.skip_docker:
            try:
                docker_manager = DockerManager()

                old_status = docker_manager.get_container_status()
                was_running = old_status.get('running', False)

                if was_running:
                    print_info('Stopping old container...')
                    docker_manager.stop_container()

                print_info('Pulling Docker image...')
                docker_manager.cleanup_old_versions()
                docker_manager.pull_image(version=new_version)
                print_success('Docker image updated')

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
